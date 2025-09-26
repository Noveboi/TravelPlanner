from core.agents.places.establishment_scout import EstablishmentScoutAgent
from core.agents.state import determine_search
from core.runners.setup import llm, example_request
from core.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    info = determine_search(example_request, llm)
    agent = EstablishmentScoutAgent(llm, FoursquareApiClient())
    report = agent.invoke(example_request, info)

    print(report.model_dump_json(indent=2))
