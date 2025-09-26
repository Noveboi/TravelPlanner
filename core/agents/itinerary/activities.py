from datetime import datetime, timedelta

from core.agents.itinerary.places import estimate_place_cost
from core.models.itinerary import ItineraryActivity, ActivityType
from core.models.places import Place, Establishment, Event, BookingType
from core.tools.spherical_distance import haversine_distance


class ItineraryActivityFactory:
    @staticmethod
    def from_place(
            place: Place,
            start_time: datetime,
            duration_hours: float,
            notes: list[str] | None = None
    ) -> ItineraryActivity:

        end_time = start_time + timedelta(hours=duration_hours)

        # Determine the activity type
        if isinstance(place, Establishment):
            activity_type = ActivityType.DINING
        elif isinstance(place, Event):
            activity_type = ActivityType.EVENT
        else:
            activity_type = ActivityType.SIGHTSEEING

        description = place.reason_to_go

        if place.weather_dependent:
            description += " (Weather dependent - check forecast!)"

        return ItineraryActivity(
            place_id=place.id,
            activity_type=activity_type,
            name=place.name,
            description=description,
            start_time=start_time,
            end_time=end_time,
            estimated_cost=estimate_place_cost(place),
            coordinates=place.coordinates,
            booking_required=place.booking_type == BookingType.REQUIRED,
            booking_url=place.website,
            notes=notes if notes is not None else []
        )


def optimize_activity_order(activities: list[ItineraryActivity], places: list[Place]) -> list[ItineraryActivity]:
    """Optimize the order of activities to minimize travel time using a nearest neighbor algorithm"""
    if len(activities) <= 2:
        return activities

    # Simple nearest neighbor optimization
    optimized = [activities[0]]  # Start with the first activity
    remaining = activities[1:]

    while remaining:
        current = optimized[-1]

        # Find the nearest remaining activity
        nearest_idx = 0
        min_distance = float('inf')

        for i, activity in enumerate(remaining):
            distance = haversine_distance(current.coordinates, activity.coordinates)
            if distance < min_distance:
                min_distance = distance
                nearest_idx = i

        # Add the nearest activity and remove from remaining
        optimized.append(remaining.pop(nearest_idx))

    # Update start/end times based on the new order
    current_time = optimized[0].start_time

    for activity in optimized:
        activity.start_time = current_time

        estimated_stay_hours = next((p.typical_hours_of_stay for p in places if p.id == activity.place_id), 2.0)

        activity.end_time = current_time + timedelta(hours=estimated_stay_hours)
        current_time = activity.end_time + timedelta(minutes=30)  # Travel buffer

    return optimized
