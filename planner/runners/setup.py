import logging
import os
from datetime import date

from langchain_openai import ChatOpenAI

from planner.models.trip import TripType, TripRequest
from planner.runners.utils import prompt_user_for_key
from planner.tools.tools import bind_necessary_tools

log = logging.getLogger('main')
logging.basicConfig(level=logging.INFO)

prompt_user_for_key('TAVILY_API_KEY')
prompt_user_for_key('OPENAI_API_KEY')

log.info('Starting')
llm = ChatOpenAI(
    model='x-ai/grok-4-fast:free',
    base_url="https://openrouter.ai/api/v1",
)
llm_with_tools = bind_necessary_tools(llm)
log.info('Got LLM model')

example_request = TripRequest(
    destination='Athens',
    start_date=date(2025, 12, 10),
    end_date=date(2025, 12, 31),
    budget=10000,
    travelers=2,
    trip_type=TripType.COUPLE,
    interests=['Sightseeing', 'Local cuisine', 'Music of any type']
)