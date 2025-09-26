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
