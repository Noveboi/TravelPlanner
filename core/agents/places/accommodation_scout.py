import operator
from typing import Annotated, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.null_checks import require
from core.agents.places.utils import convert_fsq_to_place, get_search_info, SearchInformation
from core.models.places import Place, PlaceCategory, AccommodationReport
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient, PlaceSearchRequest
from core.tools.tools import get_available_tools


class AccommodationState(BaseModel):
    trip_request: TripRequest = Field(description='The initial trip request of the user')
    search_info: SearchInformation | None = Field(
        description='Technical parameters for searching accommodations in the destination area',
        default=None
    )
    accommodations: Annotated[list[Place], operator.add] = Field(
        description='A list of the current collected accommodation places.',
        default_factory=list
    )
    report: AccommodationReport | None = Field(
        description='The final report that will be used',
        default=None
    )


class AccommodationScoutAgent(BaseAgent):
    """
    Researches hotels and places of accommodation for a given destination and curates them based on the user's travel profile.
    """

    def __init__(self, llm: BaseChatModel, client: FoursquareApiClient):
        super().__init__(name='accommodation_scout')
        self._llm = llm.bind_tools(get_available_tools())
        self._client = client
        self._workflow = self._create_workflow().compile()

    def _create_workflow(self) -> StateGraph[AccommodationState, Any, AccommodationState, AccommodationState]:
        workflow = StateGraph(
            input_schema=AccommodationState,
            state_schema=AccommodationState,
            output_schema=AccommodationState
        )

        workflow.add_node('get_destination_info', self._get_destination_information_for_search)
        workflow.add_node('find_accommodations', self._search_for_accommodations)
        workflow.add_node('generate_accommodation_report', self._get_finalized_accommodation_report)

        workflow.set_entry_point('get_destination_info')
        workflow.add_edge('get_destination_info', 'find_accommodations')
        workflow.add_conditional_edges(
            'find_accommodations',
            self._should_expand_search,
            {
                True: 'find_accommodations',
                False: 'generate_accommodation_report'
            }
        )
        workflow.set_finish_point('generate_accommodation_report')

        return workflow

    def invoke(self, request: TripRequest) -> AccommodationReport:
        self._log.info('🔎 Researching accommodations')

        initial_state = AccommodationState(
            trip_request=request
        )

        final_state = self._workflow.invoke(input=initial_state)
        report = final_state['report']

        assert isinstance(report, AccommodationReport)

        return report

    def _get_finalized_accommodation_report(self, state: AccommodationState) -> dict[str, AccommodationReport]:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=AccommodationReport
        )

        self._log.info('🏨 Generating final accommodation report...')

        prompt = f"""
                You are given a list of available accommodation options in {state.trip_request.destination} along with additional information:
                
                {state.model_dump_json()}
                
                Your task is to curate a list of accommodations that best fit the "trip request" criteria.
                
                For each recommendation pay special attention to:
                - The prices (consider the travellers' budget, group size and duration of stay)
                
                Limit your recommendations to a maximum of 10.
                """

        # noinspection PyTypeChecker
        response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})
        structured_response = response['structured_response']

        if isinstance(structured_response, list):
            return {'report': AccommodationReport(report=structured_response)}
        elif isinstance(structured_response, AccommodationReport):
            return {'report': structured_response}

        raise ValueError(f'Invalid agent output for AccommodationReport: {type(structured_response)}')

    @staticmethod
    def _should_expand_search(state: AccommodationState) -> bool:
        return not state.accommodations

    def _search_for_accommodations(self, state: AccommodationState) -> dict[str, list[Place]]:

        place_search_request = PlaceSearchRequest(
            center=require(state.search_info).reasonable_center,
            radius=require(state.search_info).search_radius,
            place_categories=[PlaceCategory.HOTEL],
            limit=35
        )

        place_search_response = require(self._client.invoke(place_search_request))

        accommodations = [convert_fsq_to_place(fsq) for fsq in place_search_response.results]

        return {'accommodations': accommodations}

    def _get_destination_information_for_search(self, state: AccommodationState) -> dict[str, SearchInformation]:
        info = get_search_info(state.trip_request, self._llm, self._log, state.search_info)
        return {'search_info': info}
