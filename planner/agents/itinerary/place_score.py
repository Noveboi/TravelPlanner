from typing import List

from planner.models.places import Place, Priority, Establishment, Event
from planner.models.trip import TripRequest, TripType


def estimate_place_cost(place: Place) -> float:
    """
    Estimate the cost for a place.
    :param place: The target
    :return: The estimated price 
    """
    # Assume the cheapest scenario always.
    match place:
        case Establishment(average_price=price):
            return price
        case Event(price_options=options):
            return min(options)
        case _:
            return 0
        


def filter_places_by_criteria(places: List[Place], trip_request: TripRequest) -> List[Place]:
    """Filter and score places based on trip criteria"""
    scored_places: list[tuple[Place, float]] = []

    for place in places:
        score = calculate_place_score(place, trip_request)
        scored_places.append((place, score))

    # Sort by score descending
    scored_places.sort(key=lambda x: x[1], reverse=True)

    max_total_activities = trip_request.total_days * 6  # 6 activities per day MAX

    # Take top-scored places within limits
    selected: list[Place] = []
    total_estimated_cost = 0.0
    budget_per_person = trip_request.budget / trip_request.travelers

    for place, score in scored_places:
        estimated_cost = estimate_place_cost(place)

        # Check if we can afford it and have space
        if len(selected) < max_total_activities and total_estimated_cost + estimated_cost <= budget_per_person * 0.8:
            selected.append(place)
            total_estimated_cost += estimated_cost

        # Always include must-see places regardless of budget if not too many
        elif place.priority == Priority.ESSENTIAL and len(selected) < max_total_activities:
            selected.append(place)

    return selected


def calculate_place_score(place: Place, trip_request: TripRequest) -> float:
    """Calculate the relevance score for a place based on the initial trip request"""
    score = 0.0

    # Priority weight (the most important factor)
    priority_weights = {
        Priority.ESSENTIAL: 10.0,
        Priority.HIGH: 7.0,
        Priority.MEDIUM: 4.0,
        Priority.LOW: 1.0
    }

    score += priority_weights[place.priority]

    # Interest matching
    place_text = f"{place.name} {place.reason_to_go}".lower()
    interest_matches = sum(1 for interest in trip_request.interests
                           if interest.lower() in place_text)
    score += interest_matches * 2.0

    # Group size considerations
    if trip_request.trip_type in [TripType.FRIENDS, TripType.GROUP]:
        # Boost restaurants and social activities
        if isinstance(place, Establishment):
            score += 1.0
    elif trip_request.trip_type == TripType.COUPLE:
        # Boost romantic spots
        romantic_keywords = ['romantic', 'sunset', 'view', 'garden', 'park']
        if any(keyword in place.reason_to_go.lower() for keyword in romantic_keywords):
            score += 1.5

    return score
