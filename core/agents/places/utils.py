from typing import Any

from core.models.geography import Coordinates
from core.models.places import Priority, BookingType, Place
from core.tools.foursquare import FoursquarePlace


def convert_fsq_to_place(fsq: FoursquarePlace):
    return Place(
        name=fsq.name,
        coordinates=Coordinates(latitude=fsq.latitude, longitude=fsq.longitude),
        priority=Priority.ESSENTIAL,
        reason_to_go='',
        website=fsq.website,
        booking_type=BookingType.REQUIRED,
        typical_hours_of_stay=0,
        weather_dependent=False
    )


def to_json(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
