import uuid
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum

from pydantic import BaseModel, Field

from .geography import Coordinates

class PlaceCategory(str, Enum):
    HOTEL = "Hotel"

class BookingType(str, Enum):
    REQUIRED = "Required"
    RECOMMENDED = "Recommended"
    NONE = "None"

class Priority(str, Enum):
    MUST_SEE = "Must See"
    SHOULD_SEE = "Should See"
    NICE_TO_SEE = "Nice to See"
    CAN_SKIP = "Can Skip"

class Place(BaseModel):
    id: uuid.UUID = uuid.uuid4()
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
    website: Optional[str] = Field(
        description="The website for the place. If there is one.",
        default=None
    )
    booking_type: BookingType = Field(
        description="Whether the place requires booking (REQUIRED), does not require booking but is typically recommended"
                    "(RECOMMENDED), or does not having any booking at all (NONE)"
    )
    typical_hours_of_stay: float = Field(
        description="The amount of time people typically spend in this place. In hours",
        ge=0,
        lt=24
    )
    weather_dependent: bool = Field(
        description="Whether the experience in this place depends on the weather"
    )
    opening_schedule: Dict[str, str] = Field(
        description="The opening hours for the place. All hours should be in the destination's local time. If an empty "
                    "dictionary is provided, it will be interpreted as 'open 24/7'.",
        examples=[
            {"Daily", "09:00-15:00"},
            {"Weekends", "08:00-20:00"},
            {"Thursday", "15:00-20:00"},
            {}
        ],
        default={}
    )
    

class Establishment(Place):
    establishment_type: str = Field(
        description="The type of the establishment",
        examples=['Restaurant', 'Cafe', 'Bar', 'Pub', 'Tavern', 'Canteen']
    )

class Landmark(Place): pass

class Event(Place):
    date_and_time: datetime = Field(description="The date and time of the event")
    price_options: List[float] = Field(description="A list of available prices, in EUR")

class Accommodation(Place):
    price_options: List[float] = Field(description="A list of available prices, in EUR")

class EventsReport(BaseModel):
    report: List[Event] = Field(description="A list of notable events taking place at the time of the trip.")

class LandmarksReport(BaseModel):
    report: List[Landmark] = Field(description="A list of the top landmarks for the destination")
    
class EstablishmentReport(BaseModel):
    report: List[Establishment] = Field(description="A list for recommended places to go eat or drink.")
    
class AccommodationReport(BaseModel):
    report: List[Accommodation] = Field(description='A list of recommended accommodations in the area.')

class DestinationReport:
    landmarks: LandmarksReport
    establishments: EstablishmentReport
    events: EventsReport
    
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
        le=50
    )