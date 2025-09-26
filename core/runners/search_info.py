from core.agents.state import determine_search
from core.runners.setup import llm, example_request

if __name__ == '__main__':
    info = determine_search(example_request, llm)

    print(info.model_dump_json(indent=2))
