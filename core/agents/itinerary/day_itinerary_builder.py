import logging
import uuid
from datetime import timedelta, datetime, time, date
from typing import TypeVar, cast, List, Iterable, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from core.agents.itinerary.activities import ItineraryActivityFactory
from core.agents.itinerary.spherical_distance import haversine_distance
from core.agents.itinerary.themes import DailyThemes
from core.agents.utils import items_of_type
from core.models.itinerary import DayItinerary, ActivityType, ItineraryActivity, TransportMode, TravelSegment
from core.models.places import Place, Establishment, Landmark, Event
from core.models.trip import TripRequest


class TravelSegmentOptions(BaseModel):
    average_public_transport_fare: float = Field(default=2.5)
    base_taxi_fare: float = Field(default=1.5)


T = TypeVar('T')

def extend_unique_until(
        dest: list[T],
        src: Iterable[T],
        target_count: int,
        key: Callable[[T], object],
) -> None:
    """
    Append items from src into dest until len(dest) == target_count,
    skipping duplicates. Key(item) determines duplicates 
    """
    seen_keys = {key(x) for x in dest}
    for item in src:
        if len(dest) >= target_count:
            break
        k = key(item)
        if k not in seen_keys:
            dest.append(item)
            seen_keys.add(k)


class ActivitySchedule(BaseModel):
    place_id: uuid.UUID = Field(
        description='The ID of the landmark/establishment/event so we can reference it easily'
    )
    start_time: time = Field(
        description='The time to begin this activity',
    )
    duration_hours: float = Field(
        description='How long this activity can last (in hours)'
    )


class DailyActivities(BaseModel):
    activities: List[ActivitySchedule] = Field(
        description='The activities for the day'
    )


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

        self._logger.info('📅 Building itineraries for each day')
        self._logger.info(f'{len(places)} Available places: {[p.name for p in places]}')
        self._logger.info(f'Available themes: {themes.list}')

        daily_itineraries: list[DayItinerary] = []
        current_date = trip_request.start_date
        options = self._get_travel_segment_options()

        available_places = places.copy()

        for day_num, theme in enumerate(themes.list, 1):
            self._logger.info(f'📅 Building itinerary for day {day_num} (theme: {theme})')

            if len(available_places) < 12:
                self._logger.info('❗ Shortage on available places. Resetting state to include all places.')
                available_places = places.copy()  # Make all places available again if we run out of places

            activities = self._build_day_activities(
                all_places=places,
                available_places=available_places,
                current_date=current_date,
                theme=theme,
                trip_request=trip_request)

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

            # Exclude the places from the current day for next days
            day_place_ids = {activity.place_id for activity in activities}
            available_places = [p for p in places if p.id not in day_place_ids]

        return daily_itineraries

    def _build_day_activities(self,
                              all_places: list[Place],
                              available_places: list[Place],
                              current_date: date,
                              trip_request: TripRequest,
                              theme: str
                              ) -> list[ItineraryActivity]:
        self._logger.info(f'🤔 Building activities with {len(available_places)} available places')

        # Separate places by type
        landmarks = items_of_type(available_places, Landmark)
        establishments = items_of_type(available_places, Establishment)
        events = [x for x in items_of_type(available_places, Event) if x.date_and_time.date() == date]

        landmarks.sort(key=lambda x: cast(Landmark, x).priority.value, reverse=True)
        establishments.sort(key=lambda x: cast(Establishment, x).priority.value, reverse=True)

        extend_unique_until(landmarks, items_of_type(all_places, Landmark), 5, key=lambda x: x.id)
        extend_unique_until(establishments, items_of_type(all_places, Establishment), 4, key=lambda x: x.id)

        prompt_landmarks = [x.model_dump() for x in landmarks]
        prompt_establishments = [x.model_dump() for x in establishments]
        prompt_events = [x.model_dump() for x in events]

        prompt = f"""
        Consider the following places:
        - Landmarks: 
        {prompt_landmarks}
        
        - Establishments (Restaurants, Cafes, etc.):
        {prompt_establishments}
        
        - Events:
        {prompt_events}
        
        Your task is to create a balanced activity schedule for the entire day and organize them based on the client's preferences:
        - Budget: {trip_request.budget} EUR
        - Interests: {trip_request.interests}
        - Group Type: {trip_request.trip_type.value}
        - The day's theme: {theme}
        """

        role = f"""
        You are a Travel Consultant based in {trip_request.destination}.
        Your job is to design personalized travel plans
        """

        response = (self._llm
        .with_structured_output(schema=DailyActivities)
        .invoke(input=[
            SystemMessage(content=role),
            HumanMessage(content=prompt)
        ]))

        return [
            ItineraryActivityFactory.from_place(
                place=next((place for place in all_places if place.id == activity.place_id)),
                start_time=datetime.combine(current_date, activity.start_time),
                duration_hours=activity.duration_hours
            ) for activity in (response.activities if isinstance(response, DailyActivities) else (
                response if isinstance(response, list) else None))
        ]

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

            if current_activity.coordinates is None or next_activity.coordinates is None:
                continue

            # This can happen, we skip here
            if current_activity.start_time == next_activity.start_time:
                continue

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
