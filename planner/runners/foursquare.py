from dotenv import load_dotenv

from planner.models.geography import Coordinates
from planner.models.places import PlaceSearchRequest
from planner.tools.foursquare import FoursquareApiClient

if __name__ == '__main__':
    load_dotenv()
    api = FoursquareApiClient()
    resp = api.invoke(PlaceSearchRequest(center=Coordinates(latitude=38.00386042829624, longitude=23.883714700651097)))
    
    if resp is not None:
        print(resp.model_dump_json(indent=2))