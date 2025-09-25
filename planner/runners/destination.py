from planner.agents.places.destination_scout import DestinationScoutAgent
from planner.setup import llm_with_tools, example_request
from planner.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    agent = DestinationScoutAgent(
        llm=llm_with_tools,
        client=FoursquareApiClient()
    )
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
