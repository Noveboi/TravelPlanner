import logging
from datetime import timedelta, datetime, time, date
from typing import cast

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from planner.agents.itinerary.activities import ItineraryActivityFactory
from planner.agents.itinerary.spherical_distance import haversine_distance
from planner.agents.itinerary.themes import DailyThemes
from planner.models.itinerary import DayItinerary, ActivityType, ItineraryActivity, TransportMode, TravelSegment
from planner.models.places import Place, Establishment, Priority, Landmark, Event
from planner.models.trip import TripRequest


class TravelSegmentOptions(BaseModel):
    average_public_transport_fare: float = Field(default=2.5)
    base_taxi_fare: float = Field(default=1.5)


class ScheduleBuilder:
    def __init__(self, llm: BaseChatModel):
        self._logger = logging.getLogger(name='day_itinerary_builder')
        self._llm = llm

    def build(self, trip_request: TripRequest, places: list[Place], themes: DailyThemes) -> list[DayItinerary]:
        """
        Constructs an itinerary for each day of the trip 
        :param trip_request: The initial trip request of the user
        :param places: The selected places to build the schedule around
        :param themes: The themes for each day
        """
        daily_itineraries: list[DayItinerary] = []
        current_date = trip_request.start_date
        options = self._get_travel_segment_options()

        for day_num, theme in enumerate(themes.list, 1):
            day_places = self._assign_places_to_day(places, theme)
            activities = self._build_day_activities(day_places, current_date)
            travel_segments = self.calculate_travel_segments(activities, options)

            total_activity_cost: float = sum(a.estimated_cost for a in activities)
            total_travel_cost: float = sum(t.total_cost for t in travel_segments)

            day_itinerary = DayItinerary(
                day_date=current_date,
                day_number=day_num,
                theme=theme,
                activities=activities,
                travel_segments=travel_segments,
                total_estimated_cost=total_activity_cost + total_travel_cost,
                key_highlights=[a.name for a in activities if a.activity_type == ActivityType.SIGHTSEEING][:3]
            )

            daily_itineraries.append(day_itinerary)
            current_date += timedelta(days=1)

        return daily_itineraries

    def _assign_places_to_day(self, places: list[Place], theme: str) -> list[Place]:
        """Assign places to specific days based on theme and other factors"""
        theme_lower = theme.lower()
        day_places = [p for p in places if self._match_specific_theme(p, theme_lower)]

        if not day_places:  # Take some places anyway
            day_places = places[:8]

            # Limit places per day based on priority
        must_see = [p for p in day_places if p.priority == Priority.ESSENTIAL]
        should_see = [p for p in day_places if p.priority == Priority.HIGH]
        nice_to_see = [p for p in day_places if p.priority == Priority.MEDIUM]

        # Build balanced day (max 6-8 activities)
        selected = must_see[:3] + should_see[:3] + nice_to_see[:2]

        return selected

    @staticmethod
    def _build_day_activities(places: list[Place], current_date: date) -> list[ItineraryActivity]:
        """Build activities for a single day"""
        activities: list[ItineraryActivity] = []

        # Start at 9 AM
        current_time = datetime.combine(current_date, time(9, 0))

        # Separate places by type
        landmarks = [cast(Landmark, p) for p in places if isinstance(p, Landmark)]
        establishments = [cast(Establishment, p) for p in places if isinstance(p, Establishment)]
        events = [cast(Event, p) for p in places if isinstance(p, Event) and p.date_and_time.date() == date]

        # Plan morning activities (9 AM-12 PM)
        morning_places = landmarks[:2] + establishments[:1]  # 1-2 sights + coffee

        for place in morning_places:
            activity = ItineraryActivityFactory.from_place(place, current_time)
            activities.append(activity)
            current_time = activity.end_time + timedelta(minutes=30)  # Travel buffer

        # Lunchtime (12 PM-2 PM)
        lunch_places = [e for e in establishments if 'restaurant' in e.establishment_type.lower()]

        if lunch_places:
            target_place = lunch_places[0]
            date_and_time = datetime.combine(current_date, time(12, 30))

            lunch_activity = ItineraryActivityFactory.from_place(target_place, date_and_time)
            lunch_activity.name = f"Lunch at {target_place.name}"

            activities.append(lunch_activity)
            current_time = lunch_activity.end_time + timedelta(minutes=15)

        # Afternoon activities (2 PM-6 PM)
        afternoon_places = landmarks[2:4] + establishments[1:2]

        for place in afternoon_places:
            if current_time.hour < 18:  # Don't go past 6 PM
                activity = ItineraryActivityFactory.from_place(place, current_time)
                activities.append(activity)
                current_time = activity.end_time + timedelta(minutes=30)

        # Add any events happening today
        for event in events:
            event_activity = ItineraryActivityFactory.from_place(event, event.date_and_time)
            activities.append(event_activity)

        # Evening meal (7 PM)
        dinner_places = [e for e in establishments if
                         'restaurant' in e.establishment_type.lower() and e not in [lunch_places[0]] if lunch_places]

        if dinner_places:
            date_and_time = datetime.combine(current_date, time(19, 0))
            dinner_place = dinner_places[0]

            dinner_activity = ItineraryActivityFactory.from_place(dinner_place, date_and_time)
            dinner_activity.name = f"Dinner at {dinner_place.name}"

            activities.append(dinner_activity)

        activities.sort(key=lambda x: x.start_time)

        return activities

    @staticmethod
    def _match_specific_theme(place: Place, theme: str) -> bool:
        """
        Try to match a place's description to a given theme.        
        :return: True if a match is found or the theme is generic, False if a match is not found.
        """

        place_text = f"{place.name} {place.reason_to_go}".lower()

        match theme:
            case 'historic':
                return any(
                    word in place_text for word in ['historic', 'old', 'ancient', 'cathedral', 'palace', 'monument'])
            case 'museum' | 'culture':
                return any(word in place_text for word in ['museum', 'gallery', 'art', 'cultural', 'exhibition'])
            case 'food' | 'market':
                return isinstance(place, Establishment) or any(
                    word in place_text for word in ['market', 'food', 'restaurant'])
            case 'nature' | 'park':
                return any(word in place_text for word in ['park', 'garden', 'nature', 'outdoor', 'beach', 'mountain'])
            case 'neighborhood' | 'neighbourhood' | 'local':
                return any(
                    word in place_text for word in ['neighborhood', 'neighbourhood', 'local', 'district', 'quarter'])
            case _:
                return True

    def _get_travel_segment_options(self) -> TravelSegmentOptions:
        prompt = """
        Search for trusted sources on transport fares. Specifically:
        - The standard public transport fare (average for buses, metro, etc.)
        - The base taxi fare
        
        Convert all currencies to EUR.
        """

        self._logger.info("🚌🚇 Searching for public transport fares")

        response = self._llm.with_structured_output(schema=TravelSegmentOptions).invoke(input=prompt)
        
        assert isinstance(response, TravelSegmentOptions)
        
        return response

    def calculate_travel_segments(self, activities: list[ItineraryActivity], options: TravelSegmentOptions) -> list[
        TravelSegment]:
        travel_segments: list[TravelSegment] = []

        for i in range(len(activities) - 1):
            current_activity = activities[i]
            next_activity = activities[i + 1]

            if current_activity.coordinates is not None and next_activity.coordinates is not None:
                segment = self.calculate_travel_segment(current_activity, next_activity, options)
                travel_segments.append(segment)

        return travel_segments

    @staticmethod
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
            total_cost=cost,
            instructions=instructions
        )
