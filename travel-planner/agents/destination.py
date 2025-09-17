from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from .coordinates import Coordinates


class Place(BaseModel):
    name: str = Field(
        description="The commonly used name for the place"
    )
    coordinates: Coordinates


class Landmark(Place): pass


class Event(Place):
    date_and_time: datetime = Field(description="The date and time of the event")
    price_options: List[float] = Field(description="A list of available prices, in EUR")


class DestinationReport(BaseModel):
    landmarks: List[Landmark] = Field(description="A list of the top landmarks for the destination")
    food_highlights: List[Place] = Field(description="A list for recommended places to go eat")
    events: List[Event] = Field(description="A list of events that take place during the trip")
    additional_places: List[Place] = Field(
        description="A list of additional places to visit. This includes any type of place not covered by the other fields of "
                    "this class. Examples include: Museums, etc...")
