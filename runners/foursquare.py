import logging

from dotenv import load_dotenv

from models.geography import Coordinates
from tools import FoursquareApiClient, PlaceSearchRequest

if __name__ == '__main__':
    load_dotenv()
    logging.basicConfig(level=logging.DEBUG)

    api = FoursquareApiClient()
    resp = api.invoke(PlaceSearchRequest(center=Coordinates(latitude=38.1, longitude=23.9)))

    if resp is not None:
        print(resp.model_dump_json(indent=2))
