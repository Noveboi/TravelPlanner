from agents.places.accommodation_scout import AccommodationScoutAgent
from runners.setup import llm, example_request
from tools import FoursquareApiClient

if __name__ == '__main__':
    fsq_client = FoursquareApiClient()
    agent = AccommodationScoutAgent(llm, fsq_client)

    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
