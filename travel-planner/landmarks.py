from agents.destination_scout import LandmarkScoutAgent
from setup import llm_with_tools, example_request
import json

if __name__ == '__main__':
    agent = LandmarkScoutAgent(llm_with_tools)
    report = agent.invoke(example_request)

    print(json.dumps(report.model_dump(), indent=2))