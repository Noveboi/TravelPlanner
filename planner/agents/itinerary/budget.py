from pydantic import BaseModel, Field

from planner.models.itinerary import DayItinerary, ActivityType
from planner.models.places import Accommodation
from planner.models.trip import TripRequest


class BudgetTracker(BaseModel):
    is_over_budget: bool = Field(
        description="Indicates if the total cost exceeds the budget"
    )


def validate_budget(request: TripRequest, itineraries: list[DayItinerary]) -> BudgetTracker:
    total_cost = sum([it.total_estimated_cost for it in itineraries])

    return BudgetTracker(
        is_over_budget=total_cost > request.budget
    )


def create_budget_breakdown(accommodation: Accommodation, itineraries: list[DayItinerary], num_people: int) -> dict[str, float]:
    """Create a breakdown of costs by category"""

    # Hotels usually adjust price for the number of guests
    accommodation_cost = min(accommodation.price_options) * len(itineraries) * num_people

    breakdown: dict[str, float] = {
        "accommodation": accommodation_cost,
        "dining": 0.0,
        "attractions": 0.0,
        "transportation": 0.0,
        "events": 0.0
    }

    for day_itinerary in itineraries:
        for activity in day_itinerary.activities:
            if activity.activity_type == ActivityType.DINING:
                breakdown["dining"] += activity.estimated_cost * num_people
            elif activity.activity_type == ActivityType.EVENT:
                breakdown["events"] += activity.estimated_cost * num_people
            else:
                breakdown["attractions"] += activity.estimated_cost

        # Add transportation costs
        for segment in day_itinerary.travel_segments:
            breakdown["transportation"] += segment.total_cost
            
    breakdown['total'] = sum(breakdown.values())

    return breakdown
