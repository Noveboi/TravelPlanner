from core.agents.places.event_scout import EventScoutAgent
from core.runners.setup import llm, example_request

if __name__ == '__main__':
    agent = EventScoutAgent(llm)
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
