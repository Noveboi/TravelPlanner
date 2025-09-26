import logging
import os
from typing import Optional, List, Any

import requests
from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from core.models.geography import Coordinates
from core.models.places import PlaceCategory, Place, Priority, BookingType

foursquare_category_map: dict[PlaceCategory, str] = {
    PlaceCategory.HOTEL: '4bf58dd8d48988d1fa931735'
}


class FoursquarePlace(BaseModel):
    fsq_place_id: str = Field()
    name: str = Field()
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    website: str | None = Field(default=None)


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
    query: str | None = Field(
        description='A string to be matched against all content for this place, including but not limited to venue name, category, telephone number, taste, and tips.',
        default=None
    )


class PlaceSearchToolInput(BaseModel):
    request: PlaceSearchRequest = Field(description='The request object used to query the Foursquare Places Search API')


class PlaceSearchTool(BaseTool):
    name: str = 'place_search'
    description: str = 'Search for places using the Foursquare Places Search API.'
    args_schema: Optional[ArgsSchema] = PlaceSearchToolInput

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._client = FoursquareApiClient()
        self._log = logging.getLogger('fsq_tool')

    def _run(self, request: PlaceSearchRequest) -> List[Place]:
        self._log.info('Invoking FSQ tool')
        response = self._client.search(request)
        return [convert_fsq_to_place(fsq_place) for fsq_place in response.results]


class FoursquareApiClient:
    """
    Interfaces with the Foursquare "Places API" to search and retrieve relevant places for a given location.
    """

    def __init__(self):
        self._log = logging.getLogger(name='fsq')
        self._base_url = 'https://places-api.foursquare.com/places'
        self._bearer_token = os.environ.get('FOURSQUARE_API_KEY')

        if self._bearer_token is None:
            self._log.warning('Foursquare API bearer token not found. Requests will not be sent.')

    def search(self, request: PlaceSearchRequest) -> FoursquarePlaceSearchResponse | None:
        """
        Calls the Foursquare "Places API" to retrieve up-to-date and relevant place information based on the given request. 
        
        :param request: Configures the API request 
        :return: A strongly typed response that contains basic place information
        """
        if self._bearer_token is None:
            return None

        fsq = self._adapt_request(request)

        headers = {
            'accept': 'application/json',
            'X-Places-Api-Version': '2025-06-17',
            'authorization': f'Bearer {self._bearer_token}'
        }

        params: dict[str, Any] = {
            'll': fsq.center,
            'radius': fsq.radius,
            'exclude_all_chains': True,
            'limit': request.limit,
            'fields': 'fsq_place_id,name,latitude,longitude,website'
        }

        if fsq.fsq_category_ids:
            params['fsq_category_ids'] = fsq.fsq_category_ids

        if request.query:
            params['query'] = request.query

        url = f'{self._base_url}/search'

        self._log.info(f'Sending Foursquare request to {url}')
        self._log.info(f'Query params: {params}')

        response = requests.get(url, params=params, headers=headers)

        self._log.info('Received response from Foursquare')

        response.raise_for_status()

        return FoursquarePlaceSearchResponse.model_validate(response.json())

    @staticmethod
    def _adapt_request(request: PlaceSearchRequest) -> FoursquarePlaceSearchRequest:
        return FoursquarePlaceSearchRequest(
            center=request.center.to_string(),
            radius=request.radius,
            fsq_category_ids=','.join([foursquare_category_map[cat] for cat in request.place_categories])
        )


def convert_fsq_to_place(fsq: FoursquarePlace):
    coordinates: Coordinates | None = Coordinates(fsq.latitude,
                                                  fsq.longitude) if fsq.latitude and fsq.longitude else None

    return Place(
        name=fsq.name,
        coordinates=coordinates,
        priority=Priority.ESSENTIAL,
        reason_to_go='',
        website=fsq.website,
        booking_type=BookingType.REQUIRED,
        typical_hours_of_stay=0,
        weather_dependent=False
    )
