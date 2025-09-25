import logging
from datetime import date

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from planner.models.trip import TripType, TripRequest
from planner.tools.tools import bind_necessary_tools

log = logging.getLogger('main')
logging.basicConfig(level=logging.INFO)

load_dotenv()

log.info('Starting')
llm = ChatOpenAI(
    model='x-ai/grok-4-fast:free',
    base_url="https://openrouter.ai/api/v1",
)
llm_with_tools = bind_necessary_tools(llm)

example_request = TripRequest(
    destination='Paris',
    start_date=date(2026, 3, 10),
    end_date=date(2025, 3, 17),
    budget=3500,
    travelers=2,
    trip_type=TripType.COUPLE,
    interests=['Explore the history of Paris', 'Taste local delicacies', 'Gardens', 'Parks']
)
