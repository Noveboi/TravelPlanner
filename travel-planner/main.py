from langchain_ollama import ChatOllama
from datetime import date
from agents.trip_analyzer import TripAnalyzerAgent
from models.trip import TravelStyle, TripType, TripRequest
import logging

logging.basicConfig(level=logging.INFO) 

log = logging.getLogger('main')

log.info('Starting')
llm = ChatOllama(model='llama3.1:latest')
log.info('Got LLM model')

agent = TripAnalyzerAgent(llm)

request = TripRequest(
    destination='Athens',
    start_date=date(2025,8,29),
    end_date=date(2025,9,3),
    budget=1250,
    travelers=2,
    travel_styles=[TravelStyle.ADVENTURE],
    trip_type=TripType.COUPLE,
    interests=['Sightseeing', 'Cuisine']
)

profile = agent.invoke(request)

print(profile)