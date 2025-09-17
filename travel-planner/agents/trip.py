from datetime import date
from enum import Enum
from typing import List, Dict

from pydantic import BaseModel, Field

class TravelStyle(Enum):
    ADVENTURE = "adventure"
    BUDGET = "budget"
    CULTURAL = "cultural"
    RELAXATION = "relaxation"

class TripType(Enum):
    SOLO = "solo"
    COUPLE = "couple"
    FRIENDS = "friends"
    GROUP = "group"

class TripRequest(BaseModel):
    destination: str = Field(
        description="The target destination city, country, or region for the trip"
    )
    start_date: date = Field(
        description="The starting date of the trip"
    )
    end_date: date = Field(
        description="The ending date of the trip"
    )
    budget: float = Field(
        description="The total budget for the trip in EUR"
    )
    travelers: int = Field(
        description="The number of people traveling together"
    )
    travel_styles: List[TravelStyle] = Field(
        description="List of preferred travel styles (adventure, budget, cultural, relaxation)"
    )
    trip_type: TripType = Field(
        description="The type of group traveling (solo, couple, friends, or group)"
    )
    interests: List[str] = Field(
        description="List of specific interests or activities the travelers want to experience"
    )

    @property
    def duration(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def format_travel_styles(self) -> str:
        return ", ".join(style.value.title() for style in self.travel_styles)

    def format_interests(self) -> str:
        return ", ".join(interest.title() for interest in self.interests)

class TripProfile(BaseModel):
    # Personality and style analysis
    preferred_activities: List[str] = Field(
        description="Recommended activities based on the traveler's interests and style"
    )
    
    # Group dynamics analysis
    group_compatibility_score: float = Field(
        description="Score from 0 to 1 indicating how well the chosen destination and activities match the group type",
        ge=0.0,
        le=1.0
    )
    group_recommendations: List[str] = Field(
        description="Specific recommendations for managing group dynamics and ensuring everyone's enjoyment"
    )
    
    # Budget analysis
    budget_alignment_score: float = Field(
        description="Score from 0 to 1 indicating how well the budget aligns with chosen destination and activities",
        ge=0.0,
        le=1.0
    )
    budget_recommendations: List[str] = Field(
        description="Suggestions for budget optimization and potential adjustments"
    )
    
    # Time management
    time_allocation: Dict[str, float] = Field(
        description="Recommended percentage of time to allocate to different types of activities",
        examples=[{"sightseeing": 0.3, "relaxation": 0.2, "adventure": 0.5}]
    )
    pace_score: float = Field(
        description="Score from 0 to 1 indicating the intensity of the planned activities (0 being very relaxed, 1 being very intense)",
        ge=0.0,
        le=1.0
    )
    
    # Enhancement recommendations
    key_recommendations: List[str] = Field(
        description="Top recommendations to enhance the trip experience"
    )
    potential_challenges: List[str] = Field(
        description="Potential challenges or considerations to be aware of"
    )
    suggested_modifications: List[str] = Field(
        description="Suggested modifications to better align the trip with preferences and constraints"
    )