import logging

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from core.models.geography import Coordinates
from core.models.places import Priority, BookingType, Place
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquarePlace
from core.tools.tools import get_available_tools

class SearchInformation(BaseModel):
    reasonable_center: Coordinates = Field(
        description='A reasonable center for the given destination location.'
    )
    search_radius: int = Field(
        description="A search radius that encompass most or all of the destination location.",
        gt=100,
        lt=100_000
    )


def convert_fsq_to_place(fsq: FoursquarePlace):
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


def get_search_info(
        request: TripRequest,
        llm: Runnable,
        log: logging.Logger,
        previous_info: SearchInformation | None
) -> SearchInformation:
    agent = create_react_agent(
        model=llm,
        tools=get_available_tools(),
        response_format=SearchInformation,
    )

    minimum_radius = 5_000 if previous_info is None else previous_info.search_radius + 5_000

    log.info('🔎 Gathering search information...')

    if previous_info is not None:
        log.info('🗺️ Expanding search radius...')

    prompt = f"""
    You are to search for places in {request.destination}.
    
    Before searching, you must find a reasonable center (latitude, longitude) and radius (in meters) to conduct the search.
    
    The radius should be at minimum {minimum_radius} meters
    """

    # noinspection PyTypeChecker
    response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})
    structured_response = response['structured_response']

    assert isinstance(structured_response, SearchInformation)
    
    log.info(f'🔎 Search in a {structured_response.search_radius}m radius at ({structured_response.reasonable_center.to_string()})')

    return structured_response