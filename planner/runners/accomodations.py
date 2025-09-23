from planner.agents.places.accommodation_scout import AccommodationScoutAgent
from planner.setup import llm_with_tools, example_request
from planner.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    fsq_client = FoursquareApiClient()
    agent = AccommodationScoutAgent(llm_with_tools, fsq_client)
    
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))