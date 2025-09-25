from datetime import date
from enum import Enum
from typing import List, Self

from pydantic import BaseModel, Field, model_validator


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
        description="The total budget for the trip in EUR",
        gt=0
    )
    travelers: int = Field(
        description="The number of people traveling together",
        gt=0
    )
    trip_type: TripType = Field(
        description="The type of group traveling (solo, couple, friends, or group)",
    )
    interests: List[str] = Field(
        description="List of specific interests or activities the travelers want to experience",
        min_length=1
    )
    
    @model_validator(mode='after')
    def verify_dates(self) -> Self:
        if self.start_date >= self.end_date:
            raise ValueError('Start date needs to be before end date')
        
        if self.end_date < date.today():
            raise ValueError('You cannot specify a trip in the past')
        
        return self

    @property
    def total_nights(self) -> int:
        return (self.end_date - self.start_date).days

    @property
    def total_days(self) -> int:
        return self.total_nights + 1

    def format_interests(self) -> str:
        return ", ".join(interest.title() for interest in self.interests)

    def format_for_llm(self) -> str:
        return f"""
        - Duration: {self.total_days} days ({self.start_date} to {self.end_date})
        - Budget: ${self.budget:,.2f} EUR
        - Group: {self.travelers} travelers - '{self.trip_type.value.title()}' trip
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
