import logging
import os
from datetime import date
from agents.trip import TravelStyle, TripType, TripRequest
from tools.tools import bind_necessary_tools
from langchain_ollama import ChatOllama

os.environ['TAVILY_API_KEY'] = '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'
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('main')

log.info('Starting')
llm = ChatOllama(model='llama3.1:latest')
llm_with_tools = bind_necessary_tools(llm)
log.info('Got LLM model')

example_request = TripRequest(
    destination='London',
    start_date=date(2025, 9, 16),
    end_date=date(2025, 9, 21),
    budget=2000,
    travelers=2,
    travel_styles=[TravelStyle.ADVENTURE],
    trip_type=TripType.COUPLE,
    interests=['Sightseeing', 'Food']
)