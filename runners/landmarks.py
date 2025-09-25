from agents.places.landmark_scout import LandmarkScoutAgent
from runners.setup import llm, example_request

if __name__ == '__main__':
    agent = LandmarkScoutAgent(llm)
    report = agent.invoke(example_request)

    print(report.model_dump_json(indent=2))
