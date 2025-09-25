from typing import List

from planner.models.places import Accommodation, Priority
from planner.models.trip import TripRequest


def select_best_accommodation(accommodations: List[Accommodation], trip_request: TripRequest) -> Accommodation:
    """Select the best accommodation based on criteria"""
    if not accommodations:
        raise ValueError("No accommodations available")

    budget_per_night_per_person = trip_request.budget / trip_request.travelers / trip_request.total_nights

    # Filter by budget
    affordable = [acc for acc in accommodations if min(acc.price_options) <= budget_per_night_per_person * 1.2]

    if not affordable: # If nothing is affordable, pick the cheapest
        return min(accommodations, key=lambda x: min(x.price_options))

    scored = []
    for acc in affordable:
        score = 0.0

        # Priority score
        priority_weights = {
            Priority.ESSENTIAL: 3,
            Priority.HIGH: 2,
            Priority.MEDIUM: 1, 
            Priority.LOW: 0
        }
        
        score += priority_weights[acc.priority]

        # cheaper is better
        max_price = max(min(a.price_options) for a in affordable)
        min_price = min(min(a.price_options) for a in affordable)
        if max_price > min_price:
            price_score = 1 - ((min(acc.price_options) - min_price) / (max_price - min_price))
            score += price_score * 2

        scored.append((acc, score))

    return max(scored, key=lambda x: x[1])[0]