from planner.agents.places.establishment_scout import EstablishmentScoutAgent
from planner.setup import llm_with_tools, example_request

if __name__ == '__main__':
    agent = EstablishmentScoutAgent(llm_with_tools)
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
