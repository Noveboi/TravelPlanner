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

    print(itinerary.model_dump_json(indent=2))
