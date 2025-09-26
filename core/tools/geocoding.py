import logging
import os
from typing import Any, Optional

import requests
from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from core.models.geography import Coordinates


class GeocodingImplicitInput(BaseModel):
    query: str = Field(description='A query for the geocoding API. Typically the official/common name of the place')


class GeocodingExplicitInput(BaseModel):
    city: str = Field(
        description='The city name. This field is required',
        examples=['Athens', 'New York']
    )
    country: str = Field(
        description='The ISO 3166-1 alpha-2 country code. This field is required',
        examples=['GR', 'US']
    )
    street: str | None = Field(
        description='The street name. This field is optional and used for scenarios where precision is necessary. '
                    '(Format: <housenumber> <streetname>)',
        examples=['555 5th Ave', '44 Tatoiou']
    )


class GeocodingToolInput(BaseModel):
    parameters: GeocodingImplicitInput | GeocodingExplicitInput = Field(
        description='Accepts either an explicit input with parameters like City, Street and Country, or an implicit input'
                    'where you can query for a place by using keywords.'
    )


class GeocodingError(BaseModel):
    description: str = Field(description='A short description of the error')
    what_to_do: str | None = Field(
        description='What action to take to try fix the error. None if no action can be taken'
    )


_GLOBAL_GEOCODE_STATE: dict[str, Any] = {
    'last_request_time': 0.0,
    'lock': None,
}


class GlobalThrottledGeocodingTool(BaseTool):
    """Geocoding tool with class-level throttling."""

    name: str = 'geocoder'
    description: str = 'Performs forward geocoding (convert address to coordinates)'
    args_schema: Optional[ArgsSchema] = GeocodingToolInput

    # Class-level shared throttling
    _throttle_interval: float = 2.0

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._api_key = os.environ.get('GEOCODE_API_KEY')
        if self._api_key is None:
            raise ValueError('Please specify "GEOCODE_API_KEY"')
        self._log = logging.getLogger('geocoding_tool')

    @staticmethod
    def _enforce_throttle() -> None:
        """Global throttling using external state."""
        import threading
        import time

        log = logging.getLogger('global_geocoding_tool')

        # Initialize lock if needed
        if _GLOBAL_GEOCODE_STATE['lock'] is None:
            _GLOBAL_GEOCODE_STATE['lock'] = threading.Lock()

        with _GLOBAL_GEOCODE_STATE['lock']:
            current_time = time.time()
            time_since_last = current_time - _GLOBAL_GEOCODE_STATE['last_request_time']

            if time_since_last < 2.0:
                sleep_time = 2.0 - time_since_last
                log.info(f'🌍 Throttling: sleeping {sleep_time:.2f}s')
                time.sleep(sleep_time)

            _GLOBAL_GEOCODE_STATE['last_request_time'] = time.time()

    def _run(self, parameters: GeocodingImplicitInput | GeocodingExplicitInput) -> Coordinates | GeocodingError:
        """Simple synchronous geocoding with global throttling."""

        try:
            self._enforce_throttle()  # This is synchronized across all tool instances
            self._log.info(f'🌍 Geocoding: {parameters}')

            # Build request
            url = 'https://geocode.maps.co/search'
            if hasattr(parameters, 'street'):
                params = {
                    'street': parameters.street,
                    'city': parameters.city,
                    'country': parameters.country,
                    'api_key': self._api_key
                }
            else:
                params = {
                    'q': parameters.query,
                    'api_key': self._api_key
                }

            # Make request
            response = requests.get(url, params=params, timeout=10)
            self._log.info(f'🌍 Response: HTTP {response.status_code}')

            # Handle response (same error handling as before)
            if response.status_code == 429:
                return GeocodingError(description="Rate limited", what_to_do='Try again')

            response.raise_for_status()
            content = response.json()

            if isinstance(content, list) and content:
                self._log.info(f'🌍 {len(content)} results for {parameters}')
                return Coordinates(latitude=content[0]['lat'], longitude=content[0]['lon'])
            elif isinstance(content, dict):
                self._log.info(f'🌍 1 result for {parameters}')
                return Coordinates(latitude=content['lat'], longitude=content['lon'])
            else:
                self._log.info(f'🌍 No result for {parameters}')
                return GeocodingError(description='Location not found', what_to_do='Try different search terms')

        except Exception as e:
            self._log.error(f'Geocoding failed: {e}')
            return GeocodingError(description=str(e), what_to_do='Try again')
