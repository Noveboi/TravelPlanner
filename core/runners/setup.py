import logging
import os
from datetime import date

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.agents.state import SearchInfo
from core.models.trip import TripType, TripRequest

log = logging.getLogger('main')
logging.basicConfig(level=logging.INFO)

load_dotenv()

log.info('Starting')
llm = ChatOpenAI(
    model='x-ai/grok-4-fast:free',
    base_url="https://openrouter.ai/api/v1",
)

example_request = TripRequest(
    destination='Athens',
    start_date=date(2026, 5, 20),
    end_date=date(2026, 5, 25),
    budget=2_000,
    travelers=2,
    trip_type=TripType.COUPLE,
    interests=['Culturally important landmarks', 'Scenic beaches', 'Parks', 'Mountain hiking for one day']
)


def ensure_api_keys_exist() -> None:
    required_keys: list[str] = [
        'TAVILY_API_KEY',
        'OPENAI_API_KEY',
        'FOURSQUARE_API_KEY'
    ]

    missing: list[str] = [f'"{k}"' for k in required_keys if not os.environ.get(k)]

    if missing:
        raise KeyError(f'Required keys are missing from the .env file: {", ".join(missing)}')
