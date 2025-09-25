import uuid
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from planner.models.geography import Coordinates
from planner.models.places import Accommodation


class ActivityType(str, Enum):
    SIGHTSEEING = "Sightseeing"
    DINING = "Dining"
    EVENT = "Event"
    TRAVEL = "Travel"
    BREAK = "Break"


class TransportMode(str, Enum):
    WALKING = "Walking"
    PUBLIC_TRANSPORT = "Public Transport"
    TAXI = "Taxi"


class ItineraryActivity(BaseModel):
    """
    Represents a single activity in the itinerary
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    place_id: Optional[uuid.UUID] = Field(
        description="Reference to the place from `DestinationReport`",
        default=None
    )
    activity_type: ActivityType = Field(description="Type of activity")
    name: str = Field(description="Name/title of the activity")
    description: str = Field(description="Brief description of what to do")
    start_time: datetime = Field(description="When the activity starts")
    end_time: datetime = Field(description="When the activity ends")
    estimated_cost: float = Field(
        description="Estimated total cost in EUR",
        default=0.0
    )
    coordinates: Coordinates = Field(
        description="Location coordinates"
    )
    booking_required: bool = Field(
        description="Whether advance booking is needed",
        default=False
    )
    booking_url: Optional[str] = Field(description="Booking website", default=None)
    notes: List[str] = Field(
        description="Additional tips or notes",
        default_factory=list
    )


class TravelSegment(BaseModel):
    """
    Represents travel between activities
    """
    from_activity_id: uuid.UUID = Field(description="Starting activity ID")
    to_activity_id: uuid.UUID = Field(description="Destination activity ID")
    transport_mode: TransportMode = Field(description="How to travel")
    duration_minutes: int = Field(description="Travel time in minutes")
    total_cost: float = Field(description="Total cost in EUR", default=0.0)
    instructions: str = Field(
        description="Specific travel instructions",
        default=""
    )


class DayItinerary(BaseModel):
    """
    Represents one day of the trip
    """
    day_date: date = Field(description="The date for this day")
    day_number: int = Field(description="Day number of the trip (1, 2, 3...)")
    theme: Optional[str] = Field(
        description="Optional theme for the day (e.g., 'Historic City Center')",
        default=None
    )
    activities: List[ItineraryActivity] = Field(description="Ordered list of activities")
    travel_segments: List[TravelSegment] = Field(
        description="Travel instructions between activities",
        default_factory=list
    )
    total_estimated_cost: float = Field(
        description="Total estimated cost for the day",
        default=0.0
    )
    key_highlights: List[str] = Field(
        description="Main highlights of the day",
        default_factory=list
    )
    weather_considerations: str = Field(
        description="Weather-related advice for the day",
        default=""
    )


class TripItinerary(BaseModel):
    """
    Complete itinerary for the entire trip
    """
    destination: str = Field(description="Trip destination")
    start_date: date = Field(description="Trip start date")
    end_date: date = Field(description="Trip end date")
    total_days: int = Field(description="Total number of days")
    daily_itineraries: List[DayItinerary] = Field(description="Day-by-day breakdown")
    accommodation: Accommodation = Field()
    total_estimated_cost: float = Field(
        description="Total trip cost estimate"
    )
    budget_breakdown: Dict[str, float] = Field(
        description="Cost breakdown by category",
        default_factory=dict
    )
