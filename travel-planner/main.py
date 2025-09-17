from langchain_ollama import ChatOllama
from datetime import date
from agents.trip_analyzer import TripAnalyzerAgent
from agents.trip import TravelStyle, TripType, TripRequest
import logging


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    log = logging.getLogger('main')
    
    log.info('Starting')
    llm = ChatOllama(model='llama3.1:latest')
    log.info('Got LLM model')
    
    agent = TripAnalyzerAgent(llm)
    
    request = TripRequest(
        destination='London',
        start_date=date(2025,9,16),
        end_date=date(2025,9,21),
        budget=2000,
        travelers=2,
        travel_styles=[TravelStyle.ADVENTURE],
        trip_type=TripType.COUPLE,
        interests=['Sightseeing', 'Food']
    )
    
    profile = agent.invoke(request)
    
    print(profile)