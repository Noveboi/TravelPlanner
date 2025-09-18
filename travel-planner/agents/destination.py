from datetime import datetime
from typing import List
from enum import Enum

from pydantic import BaseModel, Field

from .coordinates import Coordinates

class Priority(str, Enum):
    MUST_SEE = "Must See"
    SHOULD_SEE = "Should See"
    NICE_TO_SEE = "Nice to See"
    CAN_SKIP = "Can Skip"

class Place(BaseModel):
    name: str = Field(
        description="The commonly used name for the place"
    )
    coordinates: Coordinates = Field(
        description="The latitude and longitude coordinates of the place"
    )
    priority: Priority = Field(
        description="How important the place is to the overall trip experience"
    )
    reason_to_go: str = Field(
        description="A short reason why one should go to this place"
    )


class Landmark(Place): pass

class LandmarksReport(BaseModel):
    LandmarksReport: List[Landmark] = Field(description="A list of the top landmarks for the destination")

class Event(Place):
    date_and_time: datetime = Field(description="The date and time of the event")
    price_options: List[float] = Field(description="A list of available prices, in EUR")


class DestinationReport(BaseModel):
    landmarks: List[Landmark] = Field(description="A list of the top landmarks for the destination")
    food_highlights: List[Place] = Field(description="A list for recommended places to go eat")
    events: List[Event] = Field(description="A list of events that take place during the trip")
    additional_places: List[Place] = Field(
        description="A list of additional places to visit. This includes any type of place not covered by the other fields of "
                    "this class. Examples include: Museums, Malls, Amusement Parks, Specific shops, Parks, etc...")
