from core.agents.places.accommodation_scout import AccommodationScoutAgent
from core.runners.setup import llm, example_request
from core.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    fsq_client = FoursquareApiClient()
    agent = AccommodationScoutAgent(llm, fsq_client)

    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
