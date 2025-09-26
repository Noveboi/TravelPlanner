import operator
import uuid
from typing import Annotated, Any, Literal, List, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.null_checks import require
from core.agents.places.accommodation_scout import convert_fsq_to_place
from core.agents.state import SearchInfo
from core.models.places import EstablishmentReport, Place, Establishment, Priority
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient, PlaceSearchRequest
from core.tools.tools import get_available_tools


class MissingEstablishmentDetails(BaseModel):
    establishment_id: uuid.UUID = Field(
        description="The ID of the establishment this instance refers to."
    )
    average_price: float = Field(
        description="The average price for the establishment"
    )
    establishment_type: str = Field(
        description="The type of the establishment",
        examples=['Restaurant', 'Cafe', 'Bar', 'Pub', 'Tavern', 'Canteen']
    )
    average_hours_of_stay: float = Field(
        description="How many hours people typically spend in the establishment"
    )
    priority: Priority = Field(
        description="How important is it the traveller goes to this establishment?"
    )
    opening_schedule: Dict[str, str] = Field(
        description="The opening hours for the establishment.",
        examples=[
            {"Daily", "09:00-15:00"},
            {"Weekends", "08:00-20:00"},
            {"Tuesday-Saturday", "08:00-20:00"},
        ],
    )


class EstablishmentDetails(BaseModel):
    establishments: List[MissingEstablishmentDetails] = Field(
        description='A list of establishments with no missing information'
    )


class EstablishmentState(BaseModel):
    trip_request: TripRequest = Field(description='The initial trip request of the user')
    establishments_to_retrieve: int = Field(
        description='The number of establishments left to retrieve before the list is considered full'
    )
    establishments: Annotated[list[Place], operator.add] = Field(
        description='A list of the currently collected establishments',
        default_factory=list
    )
    extra_establishment_details: Annotated[list[MissingEstablishmentDetails], operator.add] = Field(
        description='A list of the currently collected additional establishment information',
        default_factory=list
    )
    report: EstablishmentReport | None = Field(
        description='The final report that will be used',
        default=None
    )
    local_info: SearchInfo = Field()


class EstablishmentScoutAgent(BaseAgent):
    """
    Researches information about restaurants, cafés, bars and more...
    """

    def __init__(self, llm: BaseChatModel, client: FoursquareApiClient):
        super().__init__('establishment_scout')
        self._llm = llm.bind_tools(get_available_tools())
        self._client = client
        self.workflow = self._create_workflow().compile()

    def _create_workflow(self) -> StateGraph[EstablishmentState, Any, EstablishmentState]:
        workflow = StateGraph(
            input_schema=EstablishmentState,
            state_schema=EstablishmentState,
            output_schema=EstablishmentState
        )

        workflow.add_node('expand_search_info', self._expand_search)
        workflow.add_node('search_establishments', self._search_establishments)
        workflow.add_node('fill_out_missing_establishment_info', self._fill_out_missing_establishment_info)
        workflow.add_node('generate_report', self._generate_report)

        workflow.set_entry_point('search_establishments')

        workflow.add_edge('expand_search_info', 'search_establishments')

        workflow.add_conditional_edges(
            'search_establishments',
            self._needs_to_search_for_more_establishments,
            {
                'yes': 'expand_search_info',
                'no': 'fill_out_missing_establishment_info'
            }
        )

        workflow.add_conditional_edges(
            'fill_out_missing_establishment_info',
            self._has_more_establishments_to_fill_out,
            {
                'yes': 'fill_out_missing_establishment_info',
                'no': 'generate_report'
            }
        )

        workflow.set_finish_point('generate_report')

        return workflow

    @staticmethod
    def _has_more_establishments_to_fill_out(state: EstablishmentState) -> Literal['yes', 'no']:
        return 'yes' if state.index < len(state.establishments) else 'no'

    def _fill_out_missing_establishment_info(self, state: EstablishmentState) -> dict[
        str, list[MissingEstablishmentDetails]]:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=EstablishmentDetails
        )

        self._log.info('🍽️ Gathering additional information for establishments')

        prompt_context = {
            'destination': state.trip_request.destination,
            'establishments': [e.model_dump() for e in state.establishments]
        }

        prompt = f"""
                You are given a list of establishments (restaurants, cafes, bars, etc.) in {state.trip_request.destination} along with additional information:
                
                {prompt_context}
                
                Your task is to gather the missing information for each establishment:
                - The average price of the establishment (per person)
                - The type of the establishment
                - Opening schedule/hours
                - Typical hours of stay (you can be granular if it is necessary)
                - The priority of the establishment
                
                Do not include/exclude any establishment from the given list
                """

        # noinspection PyTypeChecker
        response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})
        structured_response = response['structured_response']

        if isinstance(structured_response, list) and isinstance(structured_response[0], MissingEstablishmentDetails):
            return {'extra_establishment_details': structured_response}
        elif isinstance(structured_response, EstablishmentDetails):
            return {'extra_establishment_details': structured_response.establishments}

        raise ValueError(f'Invalid agent output for EstablishmentReport: {type(structured_response)}')

    def _needs_to_search_for_more_establishments(self, state: EstablishmentState) -> Literal['yes', 'no']:
        state.establishments_to_retrieve -= len(state.establishments)

        est_left = state.establishments_to_retrieve

        if est_left > 0:
            self._log.info(f'🍴 Need to search for {est_left} more establishments')
            return 'yes'

        return 'no'

    def _expand_search(self, state: EstablishmentState) -> dict[str, SearchInfo]:
        self._log.info('Expanding search')
        return {'local_info': state.local_info.expand_radius(5_000)}

    def _search_establishments(self, state: EstablishmentState) -> dict[str, list[Place]]:
        self._log.info('🍴 Searching for establishment through Foursquare')

        search_request = PlaceSearchRequest(
            center=require(state.local_info).center,
            radius=require(state.local_info).radius,
            limit=state.establishments_to_retrieve,
            query='dining'
        )

        response = require(self._client.invoke(search_request))

        establishments = [convert_fsq_to_place(fsq) for fsq in response.results]

        self._log.info(f'🍴 Got {len(establishments)} establishments')

        return {'establishments': establishments}

    def _generate_report(self, state: EstablishmentState) -> dict[str, EstablishmentReport]:
        report: list[Establishment] = []

        self._log.info('🍸 Generating final establishment report')

        for details in state.extra_establishment_details:
            target = next(x for x in state.establishments if x.id == details.establishment_id)
            establishment_dict = target.model_dump()
            details_dict = details.model_dump()

            # Join order matters here, right dict wins on key conflicts!
            report.append(Establishment.model_validate(establishment_dict | details_dict))

        return {'report': EstablishmentReport(report=report)}

    def invoke(self, request: TripRequest, info: SearchInfo) -> EstablishmentReport:
        self._log.info("🔎 Researching establishments...")

        initial_state = EstablishmentState(
            trip_request=request,
            establishments_to_retrieve=min(50, request.total_days * 5),
            local_info=info
        )

        final_state = self.workflow.invoke(input=initial_state)
        report = final_state['report']

        assert isinstance(report, EstablishmentReport)

        return report
