import core.runners.setup as base
import user_prompts as prompts
import core.agents.workflow as workflow
from core.runners.setup import example_request

if __name__ == '__main__':
    base.ensure_api_keys_exist()
    
    print("👋 Welcome!")
    
    request = prompts.create_trip_request() if prompts.should_use_preset_request() else example_request
    
    print(f'🤖 Creating your itinerary for {request.destination}, this will take a while...')
    
    itinerary = workflow.run_agent_workflow(request, base.llm)
    
    print('Finished your itinerary! It has been saved as a JSON file in the repository root.')
    
    if prompts.should_use_preset_request():
        print(itinerary.as_pretty_string())
        
    input('Press any key to exit')
    exit(0)