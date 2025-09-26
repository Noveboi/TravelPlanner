import logging
import uuid
from datetime import timedelta, datetime, time, date
from random import shuffle
from typing import TypeVar, Any, Type, cast, List, Iterable, Callable

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from core.agents.itinerary.activities import ItineraryActivityFactory
from core.agents.itinerary.spherical_distance import haversine_distance
from core.agents.itinerary.themes import DailyThemes
from core.models.itinerary import DayItinerary, ActivityType, ItineraryActivity, TransportMode, TravelSegment
from core.models.places import Place, Establishment, Priority, Landmark, Event
from core.models.trip import TripRequest


class TravelSegmentOptions(BaseModel):
    average_public_transport_fare: float = Field(default=2.5)
    base_taxi_fare: float = Field(default=1.5)


T = TypeVar('T')


def _items_of_type(items: list[Any], t: Type[T]) -> list[T]:
    return [x for x in items if isinstance(x, t)]

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

            if len(available_places) < 6:
                available_places = places.copy()  # Make all places available again if we run out of places

            day_places = self._assign_places_to_day(available_places, theme, day_num)
            activities = self._build_day_activities(
                all_places=available_places,
                available_places=day_places,
                current_date=current_date)
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
            day_ids = {p.id for p in day_places}
            available_places = [p for p in places if p.id not in day_ids]

        return daily_itineraries

    def _assign_places_to_day(self, places: list[Place], theme: str, day_num: int) -> list[Place]:
        """Assign places to specific days based on theme and other factors"""
        theme_lower = theme.lower()
        day_places = [p for p in places if self._match_specific_theme(p, theme_lower)]

        self._logger.info(f'{len(day_places)} places available for day {day_num}')

        if not day_places:  # Take some places anyway
            day_places = places[:8]

        # Limit places per day based on priority
        must_see = [p for p in day_places if p.priority == Priority.ESSENTIAL]
        should_see = [p for p in day_places if p.priority == Priority.HIGH]
        nice_to_see = [p for p in day_places if p.priority == Priority.MEDIUM]

        shuffle(must_see)
        shuffle(should_see)
        shuffle(nice_to_see)

        # Build balanced day (max 6-8 activities)
        selected = must_see[:3] + should_see[:3] + nice_to_see[:2]

        return selected

    def _build_day_activities(self, all_places: list[Place], available_places: list[Place], current_date: date) -> list[ItineraryActivity]:
        self._logger.info(f'🤔 Building activities for {current_date} and {len(available_places)} available places')

        # Separate places by type
        landmarks = _items_of_type(available_places, Landmark)
        establishments = _items_of_type(available_places, Establishment)
        events = [x for x in _items_of_type(available_places, Event) if x.date_and_time.date() == date]

        shuffle(landmarks)
        shuffle(establishments)

        landmarks.sort(key=lambda x: cast(Landmark, x).priority.value, reverse=True)
        establishments.sort(key=lambda x: cast(Establishment, x).priority.value, reverse=True)

        extend_unique_until(landmarks, _items_of_type(all_places, Landmark), 5, key=lambda x: x.id)
        extend_unique_until(establishments, _items_of_type(all_places, Establishment), 4, key=lambda x: x.id)

        prompt_landmarks = [x.model_dump() for x in landmarks[:5]]
        prompt_establishments = [x.model_dump() for x in establishments[:4]]
        prompt_events = [x.model_dump() for x in events]
        
        prompt = f"""
        Consider the following places:
        - Landmarks: 
        {prompt_landmarks}
        
        - Establishments (Restaurants, Cafes, etc.):
        {prompt_establishments}
        
        - Events:
        {prompt_events}
        
        Your task is to create activities for the entire day and organize them.
        """
        
        response = self._llm.with_structured_output(schema=DailyActivities).invoke(input=prompt)

        return [
            ItineraryActivityFactory.from_place(
                place=next((place for place in all_places if place.id == activity.place_id)),
                start_time=datetime.combine(current_date, activity.start_time),
                duration_hours=activity.duration_hours
            ) for activity in (response.activities if isinstance(response, DailyActivities) else (response if isinstance(response, list) else None))
        ]

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
