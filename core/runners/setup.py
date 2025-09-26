import logging
import os
from datetime import date

import colorlog
import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.models.trip import TripType, TripRequest

logging.basicConfig(
    level=logging.INFO,
    handlers=[colorlog.StreamHandler()],
    datefmt='%Y-%m-%d %H:%M:%S'
)

log_format = (
    "%(asctime)s "
    "[%(log_color)s%(levelname)s%(reset)s] "
    "%(log_color)s%(name)s%(reset)s: "
    "%(message)s"
)

# Update the root logger's handler with a ColoredFormatter
formatter = colorlog.ColoredFormatter(log_format)
logging.getLogger().handlers[0].setFormatter(formatter)

log = logging.getLogger('main')

load_dotenv()

log.info('Starting')
llm = ChatOpenAI(
    model='x-ai/grok-4-fast:free',
    base_url="https://openrouter.ai/api/v1",
    timeout=httpx.Timeout(connect=20, read=180, write=180, pool=30),
    max_retries=2
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
