import datetime
import json

from planner.agents.itinerary.itinerary_agent import ItineraryBuilderAgent
from planner.agents.places.destination_scout import DestinationScoutAgent
from planner.setup import log, llm_with_tools, example_request
from planner.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    scout_agent = DestinationScoutAgent(
        llm=llm_with_tools,
        client=FoursquareApiClient()
    )
    
    report = scout_agent.invoke(example_request)
    log.info('Finished scouting')
    itinerary_agent = ItineraryBuilderAgent(llm_with_tools)
    
    itinerary = itinerary_agent.invoke(example_request, report)

    file_name = f'{example_request.destination.lower()}_itinerary_{datetime.datetime.now()}'

    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(itinerary.model_dump(), f, indent=4, ensure_ascii=False)

    print('Done!')