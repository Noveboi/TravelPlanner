import logging
import os
from typing import Optional, List

import requests
from pydantic import BaseModel, Field

from planner.models.geography import Coordinates
from planner.models.places import PlaceCategory

foursquare_category_map: dict[PlaceCategory, str] = {
    PlaceCategory.HOTEL: '4bf58dd8d48988d1fa931735'
}


class FoursquareDayHours(BaseModel):
    close: str = Field()
    day: int = Field()
    open: str = Field()


class FoursquareHours(BaseModel):
    display: str = Field()
    regular: list[FoursquareDayHours] = Field()


class FoursquarePlace(BaseModel):
    fsq_place_id: str = Field()
    latitude: float = Field()
    longitude: float = Field()
    name: str = Field()
    website: Optional[str] = Field(default=None)


class FoursquarePlaceSearchRequest:
    def __init__(self, center: str, radius: int, fsq_category_ids: str):
        self.center = center
        self.radius = radius
        self.fsq_category_ids = fsq_category_ids


class FoursquarePlaceSearchResponse(BaseModel):
    results: list[FoursquarePlace] = Field()


class PlaceSearchRequest(BaseModel):
    center: Coordinates = Field(description='The latitude/longitude around which to retrieve place information.')
    radius: int = Field(
        description='Radius distance (in meters) used to define an area to bias search results.',
        gt=0,
        lt=100_000,
        default=22_000
    )
    place_categories: List[PlaceCategory] = Field(
        description='Filter the response and return places matching the specified categories.',
        default=[]
    )
    limit: int = Field(
        description="Limit the number of results",
        gt=0,
        le=50,
        default=35
    )


class FoursquareApiClient:
    """
    Interfaces with the Foursquare "Places API" to search and retrieve relevant places for a given location.
    """

    def __init__(self):
        self._logger = logging.getLogger(name='fsq')
        self._base_url = 'https://places-api.foursquare.com/places'
        self._bearer_token = os.environ.get('FOURSQUARE_API_KEY')

        if self._bearer_token is None:
            self._logger.warning('Foursquare API bearer token not found. Requests will not be sent.')

    def invoke(self, request: PlaceSearchRequest) -> FoursquarePlaceSearchResponse | None:
        """
        Calls the Foursquare "Places API" to retrieve up-to-date and relevant place information based on the given request. 
        
        :param request: Configures the API request 
        :return: A strongly typed response that contains basic place information
        """
        if self._bearer_token is None:
            return None

        self._logger.info('Sending Foursquare request...')

        fsq = self._adapt_request(request)

        headers = {
            'accept': 'application/json',
            'X-Places-Api-Version': '2025-06-17',
            'authorization': f'Bearer {self._bearer_token}'
        }

        params = {
            'll': fsq.center,
            'radius': fsq.radius,
            'exclude_all_chains': True,
            'limit': request.limit,
            # 'fields': 'fsq_place_id,latitude,longitude,name,website,description,hours'
        }

        if len(fsq.fsq_category_ids) > 0:
            params['fsq_category_ids'] = fsq.fsq_category_ids

        self._logger.info('Sending request to Foursquare')
        response = requests.get(self._base_url + '/search', params=params, headers=headers)
        self._logger.info('Received response from Foursquare')

        response.raise_for_status()

        return FoursquarePlaceSearchResponse.model_validate(response.json())

    @staticmethod
    def _adapt_request(request: PlaceSearchRequest) -> FoursquarePlaceSearchRequest:
        return FoursquarePlaceSearchRequest(
            center=request.center.to_string(),
            radius=request.radius,
            fsq_category_ids=','.join([foursquare_category_map[cat] for cat in request.place_categories])
        )
