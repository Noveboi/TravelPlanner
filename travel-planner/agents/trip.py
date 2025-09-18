from datetime import date
from enum import Enum
from typing import List

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
    
    def format_for_llm(self) -> str:
        return f"""
        - Duration: {self.duration} days ({self.start_date} to {self.end_date})
        - Budget: ${self.budget:,.2f} EUR
        - Group: {self.travelers} travelers - '{self.trip_type.value.title()}' trip
        - Travel Style(s): {self.format_travel_styles()}
        - Interests: {self.format_interests()}
        """


class GeneralTripAnalysis(BaseModel):
    group_focus: List[str] = Field(
        description="Keywords that describe what the group should focus on."
    )
    group_recommendations: List[str] = Field(
        description="Specific recommendations for managing group dynamics and ensuring everyone's enjoyment"
    )

    # Enhancement recommendations
    key_recommendations: List[str] = Field(
        description="Top recommendations to enhance the trip experience"
    )
    potential_challenges: List[str] = Field(
        description="Potential challenges or considerations to be aware of"
    )
