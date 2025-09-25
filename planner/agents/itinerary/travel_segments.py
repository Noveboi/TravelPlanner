from typing import NamedTuple

from planner.agents.itinerary.spherical_distance import haversine_distance
from planner.models.itinerary import ItineraryActivity, TransportMode, TravelSegment


class TravelSegmentOptions(NamedTuple):
    average_public_transport_fare: float = 2.5
    base_taxi_fare: float = 1.5


def calculate_travel_segment(
        from_activity: ItineraryActivity, 
        to_activity: ItineraryActivity, 
        options: TravelSegmentOptions
) -> TravelSegment:
    """Calculate travel between two activities"""

    distance_km = haversine_distance(from_activity.coordinates, to_activity.coordinates)

    if distance_km <= 0.5:
        transport_mode = TransportMode.WALKING
        duration_minutes = max(5, int(distance_km * 12))  # 12 min per km walking
        cost = 0.0
        instructions = f"Walk {int(distance_km * 1000)}m to {to_activity.name} ({duration_minutes} mins)"
    elif distance_km <= 3:
        transport_mode = TransportMode.PUBLIC_TRANSPORT
        duration_minutes = max(10, int(distance_km * 8))  # 8 min per km public transport
        cost = options.average_public_transport_fare  # Average public transport fare
        instructions = f"Take public transport to {to_activity.name} ({duration_minutes} mins, €{cost:.2f})"
    else:
        transport_mode = TransportMode.TAXI
        duration_minutes = max(15, int(distance_km * 5))  # 5 min per km by car
        cost = options.base_taxi_fare + (distance_km * 1.20)  # Base fare + per km
        instructions = f"Take taxi to {to_activity.name} ({duration_minutes} mins, ~€{cost:.2f})"

    return TravelSegment(
        from_activity_id=from_activity.id,
        to_activity_id=to_activity.id,
        transport_mode=transport_mode,
        duration_minutes=duration_minutes,
        cost=cost,
        instructions=instructions
    )