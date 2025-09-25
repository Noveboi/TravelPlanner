import operator
from typing import Annotated, Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.null_checks import require
from core.agents.places.accommodation_scout import SearchInformation, get_search_info, convert_fsq_to_place
from core.models.places import EstablishmentReport, Place
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient, PlaceSearchRequest
from core.tools.tools import get_available_tools


class EstablishmentState(BaseModel):
    trip_request: TripRequest = Field(description='The initial trip request of the user')
    establishments_to_retrieve: int = Field(
        description='The number of establishments left to retrieve before the list is considered full'
    )
    search_info: SearchInformation | None = Field(
        description="Technical parameters for searching establishments in the destination area",
        default=None
    )
    establishments: Annotated[list[Place], operator.add] = Field(
        description='A list of the currently collected establishments',
        default_factory=list
    )
    report: EstablishmentReport | None = Field(
        description='The final report that will be used',
        default=None
    )

class EstablishmentScoutAgent(BaseAgent):
    """
    Researches information about restaurants, cafés, bars and more...
    """

    def __init__(self, llm: BaseChatModel, client: FoursquareApiClient):
        super().__init__('establishment_scout')
        self._llm = llm.bind_tools(get_available_tools())
        self._client = client
        self._structured_llm = llm.with_structured_output(schema=EstablishmentReport)
        self._workflow = self._create_workflow().compile()

    def _create_workflow(self) -> StateGraph[EstablishmentState, Any, EstablishmentState]:
        workflow = StateGraph(
            input_schema=EstablishmentState,
            state_schema=EstablishmentState,
            output_schema=EstablishmentState
        )
        
        workflow.add_node('create_search_info', self._get_search_info)
        workflow.add_node('search_establishments', self._search_establishments)
        workflow.add_node('generate_report', self._generate_report)
        
        workflow.set_entry_point('create_search_info')
        workflow.add_edge('create_search_info', 'search_establishments')
        
        workflow.add_conditional_edges(
            'search_establishments',
            self._needs_to_search_for_more_establishments,
            {
                'yes': 'create_search_info',
                'no': 'generate_report'
            })
        
        workflow.set_finish_point('generate_report')
        
        return workflow
        
    def _needs_to_search_for_more_establishments(self, state: EstablishmentState) -> Literal['yes', 'no']:
        state.establishments_to_retrieve -= len(state.establishments)
        
        est_left = state.establishments_to_retrieve
        
        if est_left > 0:
            self._log.info(f'🍴 Need to search for {est_left} more establishments')
            return 'yes'
        
        return 'no'
    
    def _get_search_info(self, state: EstablishmentState) -> dict[str, SearchInformation]:
        info = get_search_info(state.trip_request, self._llm, self._log, state.search_info)
        return { 'search_info': info }
    
    def _search_establishments(self, state: EstablishmentState) -> dict[str, list[Place]]:
        self._log.info('🍴 Searching for establishment through Foursquare')
        
        search_request = PlaceSearchRequest(
            center=require(state.search_info).reasonable_center,
            radius=require(state.search_info).search_radius,
            query='dining',
            limit=state.establishments_to_retrieve
        )
        
        response = require(self._client.invoke(search_request))
        
        establishments = [convert_fsq_to_place(fsq) for fsq in response.results]
        return { 'establishments': establishments }
    
    def _generate_report(self, state: EstablishmentState) -> dict[str, EstablishmentReport]:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=EstablishmentReport
        )
        
        self._log.info('🍽️🍸 Generating final establishment report')
        
        prompt = f"""
                You are given a list of establishments (restaurants, cafes, bars, etc.) in {state.trip_request.destination} along with additional information:
                
                {state.model_dump_json()}
                
                Your task is to fill in the missing information for each establishment:
                - The average price of the establishment (per person)
                - The type of the establishment
                - Opening schedule/hours
                - Typical hours of stay (you can be granular if it is necessary)
                
                Additionally, change the priority field if necessary.
                
                Do not include/exclude any establishment from the given list
                """

        # noinspection PyTypeChecker
        response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})
        structured_response = response['structured_response']

        if isinstance(structured_response, list):
            return {'report': EstablishmentReport(report=structured_response)}
        elif isinstance(structured_response, EstablishmentReport):
            return {'report':structured_response}

        raise ValueError(f'Invalid agent output for EstablishmentReport: {type(structured_response)}')

    def invoke(self, request: TripRequest) -> EstablishmentReport:
            self._log.info("🔎 Researching establishments...")
            
            initial_state = EstablishmentState(
                trip_request=request,
                establishments_to_retrieve=min(20, request.total_days * 4)
            )
            
            final_state = self._workflow.invoke(input=initial_state)
            report = final_state['report']
            
            assert isinstance(report, EstablishmentReport)
            
            return report