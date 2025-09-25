from typing import List

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from planner.agents.base import BaseAgent
from planner.models.geography import Coordinates
from planner.models.places import Place, Priority, BookingType, PlaceCategory, AccommodationReport
from planner.models.trip import TripRequest
from planner.tools.foursquare import FoursquareApiClient, FoursquarePlace, PlaceSearchRequest
from planner.tools.tools import get_available_tools


class TripDestinationInformation(BaseModel):
    reasonable_center: Coordinates = Field(
        description='A reasonable center for the given destination location.'
    )
    accommodation_search_radius: int = Field(
        description="A search radius that encompass most or all of the destination location.",
        gt=100,
        lt=100_000
    )


class InitialAccommodationReport(BaseModel):
    report: List[Place] = Field(description="A list of found accommodations")


class AccommodationScoutAgent(BaseAgent):
    """
    Researches hotels and places of accommodation for a given destination and curates them based on the user's travel profile.
    """
    def __init__(self, llm: BaseLanguageModel, client: FoursquareApiClient):
        super().__init__(name='accommodation_scout', llm=llm)
        self._client = client

    def invoke(self, request: TripRequest) -> AccommodationReport:
        info = self._get_destination_information_for_search(request)

        self._logger.info(f'Got destination information: {info.model_dump_json(indent=2)}')

        initial_report = self.get_initial_accommodation_report(info)
        final_report = self.get_finalized_accommodation_report(request, initial_report)

        return final_report

    def get_finalized_accommodation_report(self, req: TripRequest,
                                           initial_report: InitialAccommodationReport) -> AccommodationReport:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=AccommodationReport
        )

        self._logger.info('Generating final accommodation report...')

        prompt = f"""
                You are given a list of available accommodation options in {req.destination}:
                
                {initial_report.model_dump_json()}
                
                Consider also the following travel request:
                
                {req.format_for_llm()}
                
                Your task is to curate a list of accommodations that best fit the travel request criteria.
                
                For each recommendation pay special attention to:
                - The prices (consider the travellers' budget, group size and duration of stay)
                
                Limit your recommendations to a maximum of 10.
                """

        # noinspection PyTypeChecker
        response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})

        return response['structured_response']

    def get_initial_accommodation_report(self, info: TripDestinationInformation) -> InitialAccommodationReport:
        place_search_request = PlaceSearchRequest(
            center=info.reasonable_center,
            radius=info.accommodation_search_radius,
            place_categories=[PlaceCategory.HOTEL],
            limit=35
        )

        place_search_response = self._client.invoke(place_search_request)
        accommodation_report = [self._convert_fsq_to_place(fsq) for fsq in place_search_response.results]

        return InitialAccommodationReport(report=accommodation_report)

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

    def _get_destination_information_for_search(self, req: TripRequest) -> TripDestinationInformation:
        agent = create_react_agent(
            model=self._llm,
            tools=get_available_tools(),
            response_format=TripDestinationInformation,
        )

        self._logger.info('Gathering information about the destination...')
        prompt = f"""
You are to search for accommodations in {req.destination}.
Before searching, find a reasonable center (latitude, longitude) and radius (in meters) to conduct the search.
"""

        # noinspection PyTypeChecker
        response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})

        return response['structured_response']
