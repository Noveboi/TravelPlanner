from agents.places.destination_scout import DestinationScoutAgent
from runners.setup import example_request, llm
from tools import FoursquareApiClient

if __name__ == '__main__':
    agent = DestinationScoutAgent(
        llm=llm,
        client=FoursquareApiClient()
    )
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
