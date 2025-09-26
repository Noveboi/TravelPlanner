import logging
import os
from typing import Optional, Any

import requests
from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from core.models.geography import Coordinates


class GeocodingToolInput(BaseModel):
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


class GeocodingError(BaseModel):
    description: str = Field(description='A short description of the error')
    what_to_do: str | None = Field(
        description='What action to take to try fix the error. None if no action can be taken'
    )


class GeocodingToolApiClient:
    def __init__(self):
        self._api_key = os.environ.get('GEOCODE_API_KEY')
        if self._api_key is None:
            raise ValueError('Please specify "GEOCODE_API_KEY". Go to https://geocode.maps.co/')
        self._log = logging.getLogger('geocoding_api_client')
        self._base_url = 'https://geocode.maps.co'

    def get(self, city: str, country: str, street: str | None) -> Coordinates | GeocodingError:
        url: str = f'{self._base_url}/search'
        params: dict[str, str] = {
            'street': street,
            'city': city,
            'country': country,
            'api_key': self._api_key
        }

        response = requests.get(url, params=params)

        if response.status_code == 429:
            self._log.warning('Throttle required')
            return GeocodingError(
                description=f"You've exceeded the request limit (error: {response.text})",
                what_to_do='Wait 1 second and then call again.'
            )

        if response.status_code == 503:
            return GeocodingError(
                description="The server of the external API is receiving extremely high traffic.",
                what_to_do='Stop using this service.'
            )

        if response.status_code == 403:
            self._log.error('Client blocked from Geocode API!')
            return GeocodingError(
                description='We have been blocked from sending requests.',
                what_to_do='Stop using this service.'
            )

        response.raise_for_status()

        content = response.json()

        def get_coordinates(x: dict[str, Any]) -> Coordinates:
            return Coordinates(
                latitude=x['lat'],
                longitude=x['lon']
            )

        if isinstance(content, dict):
            return get_coordinates(content)

        if isinstance(content, list):
            if not content:
                return GeocodingError(
                    description='Place not found',
                    what_to_do='Try a different name for the place'
                )

            return get_coordinates(content[0])

        raise ValueError(f'Unexpected response format from geocode: {content}')


class ForwardGeocodingTool(BaseTool):
    name: str = 'geocoder'
    description: str = (
        'Performs forward geocoding (convert address to coordinates). Use this tool with care because it '
        'calls an external API')
    args_schema: Optional[ArgsSchema] = GeocodingToolInput

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._client = GeocodingToolApiClient()

    def _run(self, city: str, country: str, street: str | None) -> Coordinates | GeocodingError:
        """
        Use the tool
        
        :returns A Coordinates object (latitude, longitude) when found, None otherwise.
        """
        response = self._client.get(city, country, street)
        return response
