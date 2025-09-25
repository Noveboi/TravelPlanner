from core.agents.places.establishment_scout import EstablishmentScoutAgent
from core.runners.setup import llm, example_request

if __name__ == '__main__':
    agent = EstablishmentScoutAgent(llm)
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
