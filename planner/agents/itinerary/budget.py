from pydantic import BaseModel, Field

from planner.models.itinerary import DayItinerary, ActivityType
from planner.models.trip import TripRequest


class BudgetTracker(BaseModel):
    total_estimated_cost: float = Field(
        description="The total estimated cost of the entire trip",
        ge=0
    )
    is_over_budget: bool = Field(
        description="Indicates if the total cost exceeds the budget"
    )


def validate_budget(request: TripRequest, itineraries: list[DayItinerary]) -> BudgetTracker:
    total_cost = sum([it.total_estimated_cost for it in itineraries])

    return BudgetTracker(
        total_estimated_cost=total_cost,
        is_over_budget=total_cost > request.budget
    )


def create_budget_breakdown(daily_itineraries: list[DayItinerary]) -> dict[str, float]:
    """Create a breakdown of costs by category"""

    breakdown = {
        "accommodation": 0.0,
        "dining": 0.0,
        "attractions": 0.0,
        "transportation": 0.0,
        "events": 0.0
    }
    
    for day_itinerary in daily_itineraries:
        for activity in day_itinerary.activities:
            if activity.activity_type == ActivityType.DINING:
                breakdown["dining"] += activity.estimated_cost
            elif activity.activity_type == ActivityType.EVENT:
                breakdown["events"] += activity.estimated_cost
            else:
                breakdown["attractions"] += activity.estimated_cost

        # Add transportation costs
        for segment in day_itinerary.travel_segments:
            breakdown["transportation"] += segment.total_cost

    return breakdown
