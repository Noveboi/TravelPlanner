from core.agents.places.establishment_scout import EstablishmentScoutAgent
from core.runners.setup import llm, example_request
from core.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    agent = EstablishmentScoutAgent(llm, FoursquareApiClient())
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
