from time import sleep

import core.agents.workflow as workflow
import core.runners.setup as base
import user_prompts as prompts
from core.runners.setup import example_request

if __name__ == '__main__':
    base.ensure_api_keys_exist()

    print("👋 Welcome!")

    request = example_request if prompts.should_use_preset_request() else prompts.create_trip_request()

    print(f'🤖 Creating your itinerary for {request.destination}, this will take a while...')

    itinerary = workflow.run_agent_workflow(request, base.llm, base.log)

    sleep(0.3)

    with open(f'{request.destination.lower()}_itinerary.json', 'w', encoding='utf-8') as f:
        f.write(itinerary.model_dump_json(indent=4))

    print('Finished your itinerary! It has been saved as a JSON file in the repository root.')
