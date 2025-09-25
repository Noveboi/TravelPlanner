import operator
from typing import Annotated, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.null_checks import require
from core.models.geography import Coordinates
from core.models.places import Place, Priority, BookingType, PlaceCategory, AccommodationReport
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient, FoursquarePlace, PlaceSearchRequest
from core.tools.tools import get_available_tools


class TripDestinationInformation(BaseModel):
    reasonable_center: Coordinates = Field(
        description='A reasonable center for the given destination location.'
    )
    search_radius: int = Field(
        description="A search radius that encompass most or all of the destination location.",
        gt=100,
        lt=100_000
    )


class AccommodationState(BaseModel):
    trip_request: TripRequest = Field(description='The initial trip request of the user')
    destination_info: TripDestinationInformation | None = Field(
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
        self._logger.info('🔎 Researching accommodations')

        initial_state = AccommodationState(
            trip_request=request
        )

        final_state = self._workflow.invoke(input=initial_state)
        report = final_state['report']

        if isinstance(report, list):
            return AccommodationReport(report=report)
        elif isinstance(report, AccommodationReport):
            return report

        raise ValueError(f'Invalid agent output for AccommodationReport: {type(report)}')

    def _get_finalized_accommodation_report(self, state: AccommodationState) -> dict[str, AccommodationReport]:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=AccommodationReport
        )

        self._logger.info('🏨 Generating final accommodation report...')

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

        return response['structured_response']

    @staticmethod
    def _should_expand_search(state: AccommodationState) -> bool:
        return not state.accommodations

    def _search_for_accommodations(self, state: AccommodationState) -> dict[str, list[Place]]:

        place_search_request = PlaceSearchRequest(
            center=require(state.destination_info).reasonable_center,
            radius=require(state.destination_info).search_radius,
            place_categories=[PlaceCategory.HOTEL],
            limit=35
        )

        place_search_response = require(self._client.invoke(place_search_request))

        accommodations = [self._convert_fsq_to_place(fsq) for fsq in place_search_response.results]

        return {'accommodations': accommodations}

    @staticmethod
    def _convert_fsq_to_place(fsq: FoursquarePlace):
        return Place(
            name=fsq.name,
            coordinates=Coordinates(latitude=fsq.latitude, longitude=fsq.longitude),
            priority=Priority.ESSENTIAL,
            reason_to_go='',
            website=fsq.website,
            booking_type=BookingType.REQUIRED,
            typical_hours_of_stay=0,
            weather_dependent=False
        )

    def _get_destination_information_for_search(self, state: AccommodationState) -> dict[
        str, TripDestinationInformation]:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=TripDestinationInformation,
        )

        minimum_radius = 5_000 if state.destination_info is None else state.destination_info.search_radius + 5_000

        self._logger.info('🔎 Gathering information about the destination...')

        if state.destination_info is not None:
            self._logger.info('🗺️ Expanding search radius...')

        prompt = f"""
        You are to search for accommodations in {state.trip_request.destination}.
        
        Before searching, find a reasonable center (latitude, longitude) and radius (in meters) to conduct the search.
        
        The radius should be at minimum {minimum_radius} meters
        """

        # noinspection PyTypeChecker
        response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})

        return {'destination_info': response['structured_response']}
