import operator
from typing import Annotated, Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.null_checks import require
from core.agents.state import SearchInfo
from core.models.places import Place, PlaceCategory, AccommodationReport
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient, PlaceSearchRequest, convert_fsq_to_place
from core.tools.tools import get_available_tools
from core.utils import invoke_react_agent


class AccommodationState(BaseModel):
    trip_request: TripRequest = Field(description='The initial trip request of the user')
    accommodations: Annotated[list[Place], operator.add] = Field(
        description='A list of the current collected accommodation places.',
        default_factory=list
    )
    report: AccommodationReport | None = Field(
        description='The final report that will be used',
        default=None
    )
    local_info: SearchInfo = Field()


class AccommodationScoutAgent(BaseAgent):
    """
    Researches hotels and places of accommodation for a given destination and curates them based on the user's travel profile.
    """

    def __init__(self, llm: BaseChatModel, client: FoursquareApiClient):
        super().__init__(name='accommodation_scout')
        self._llm = llm.bind_tools(get_available_tools())
        self._client = client
        self.workflow = self._create_workflow().compile()

    def _create_workflow(self) -> StateGraph[AccommodationState, Any, AccommodationState, AccommodationState]:
        workflow = StateGraph(
            input_schema=AccommodationState,
            state_schema=AccommodationState,
            output_schema=AccommodationState
        )

        workflow.add_node('expand_search', self._expand_search)
        workflow.add_node('find_accommodations', self._search_for_accommodations)
        workflow.add_node('generate_accommodation_report', self._get_finalized_accommodation_report)

        workflow.set_entry_point('find_accommodations')
        workflow.add_conditional_edges(
            'find_accommodations',
            self._has_no_accommodations,
            {
                'has_no_accommodations': 'expand_search',
                'found_accommodations': 'generate_accommodation_report'
            }
        )

        workflow.add_edge('expand_search', 'find_accommodations')

        workflow.set_finish_point('generate_accommodation_report')

        return workflow

    def invoke(self, request: TripRequest, info: SearchInfo) -> AccommodationReport:
        self._log.info('🔎 Researching accommodations')

        initial_state = AccommodationState(
            trip_request=request,
            local_info=info
        )

        final_state = self.workflow.invoke(input=initial_state)
        report = final_state['report']

        assert isinstance(report, AccommodationReport)

        return report

    def _get_finalized_accommodation_report(self, state: AccommodationState) -> dict[str, AccommodationReport]:
        self._log.info('🏨 Generating final accommodation report...')

        prompt = f"""
                You are given a list of available accommodation options in {state.trip_request.destination} along with additional information:
                
                {state.model_dump_json()}
                
                Your task is to curate a list of accommodations that best fit the "trip request" criteria.
                
                For each recommendation pay special attention to:
                - The prices (consider the travellers' budget, group size and duration of stay)
                
                Limit your recommendations to a maximum of 10.
                """

        return {'report': invoke_react_agent(self._llm, [HumanMessage(prompt)], schema=AccommodationReport)}

    @staticmethod
    def _has_no_accommodations(state: AccommodationState) -> Literal['has_no_accommodations', 'found_accommodations']:
        return 'has_no_accommodations' if not state.accommodations else 'found_accommodations'

    def _search_for_accommodations(self, state: AccommodationState) -> dict[str, list[Place]]:
        place_search_request = PlaceSearchRequest(
            center=require(state.local_info).center,
            radius=require(state.local_info).radius,
            place_categories=[PlaceCategory.HOTEL],
            limit=35
        )

        place_search_response = require(self._client.search(place_search_request))

        accommodations = [convert_fsq_to_place(fsq) for fsq in place_search_response.results]

        return {'accommodations': accommodations}

    @staticmethod
    def _expand_search(state: AccommodationState) -> dict[str, SearchInfo]:
        return {'local_info': state.local_info.expand_radius(7_500)}
