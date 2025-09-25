import logging

from langchain_core.language_models import BaseChatModel

from core.agents.itinerary.itinerary_agent import ItineraryBuilderAgent
from core.agents.places.destination_scout import DestinationScoutAgent
from core.models.itinerary import TripItinerary
from core.models.places import DestinationReport
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient


def run_agent_workflow(request: TripRequest, llm: BaseChatModel, log: logging.Logger) -> TripItinerary:
    log.info(f'Received trip request: \n{request.model_dump_json(indent=2)}')

    scout_agent_workflow = DestinationScoutAgent(llm=llm, client=FoursquareApiClient())
    itinerary_agent_workflow = ItineraryBuilderAgent(llm=llm)

    destination_report: DestinationReport = scout_agent_workflow.invoke(request)
    assert isinstance(destination_report, DestinationReport)

    itinerary: TripItinerary = itinerary_agent_workflow.invoke(request, destination_report)
    assert isinstance(itinerary, TripItinerary)

    return itinerary
