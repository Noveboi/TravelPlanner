from datetime import time, datetime, timedelta
from typing import List, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompt_values import PromptValue
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from planner.agents.base import BaseAgent
from planner.agents.itinerary.accommodation_choice import select_best_accommodation
from planner.agents.itinerary.day_itinerary_builder import ScheduleBuilder
from planner.agents.itinerary.spherical_distance import haversine_distance
from planner.agents.itinerary.place_score import filter_places_by_criteria
from planner.agents.itinerary.travel_segments import calculate_travel_segment, TravelSegmentOptions
from planner.models.itinerary import DayItinerary, TripItinerary, ItineraryActivity, ActivityType, TransportMode, \
    TravelSegment
from planner.models.places import DestinationReport, Place, Accommodation, BookingType
from planner.models.trip import TripRequest


class BudgetTracker(BaseModel):
    pass


class DailyThemes(BaseModel):
    list: List[str] = Field(description="A list containing a theme for each day of the trip")

    def add_additional_themes_if_incomplete(self, required_num: int) -> None:
        self.list.extend([f"Exploration Day {i + 1}" for i in range(len(list), required_num)])


class ItineraryAgentInput(BaseModel):
    trip_request: TripRequest = Field(
        description="The user's initial input."
    )
    destination_report: DestinationReport = Field(
        description="Contains detailed place information on accommodations, establishments, events and landmarks"
    )


class ItineraryState(BaseModel):
    """State object passed between nodes in the itinerary building workflow"""
    trip_request: TripRequest = Field(
        description="The user's initial input."
    )
    destination_report: DestinationReport = Field(
        description="Contains detailed place information on accommodations, establishments, events and landmarks"
    )
    selected_places: List[Place] = Field(
        description="A list of filtered and prioritized places, curated algorithmically"
    )
    daily_themes: DailyThemes = Field()
    accommodation_activities: List[ItineraryActivity] = Field(
        description="Activities for accommodation for each night."
    )
    daily_itineraries: List[DayItinerary] = Field(
        description="An itinerary for each day of the trip"
    )
    final_itinerary: Optional[TripItinerary] = Field(
        description="The final itinerary containing all the relevant information",
        default=None
    )
    budget_tracker: BudgetTracker = Field(
        description="A budget tracker for ensuring we do not go over-budget"
    )
    errors: List[str] = Field(
        description="A list of errors for unexpected scenarios"
    )


class ItineraryBuilderAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__(name='itinerary_builder', llm=llm)
        self.theme_llm = llm.with_structured_output(schema=DailyThemes)
        self.travel_segment_helper_llm = llm.with_structured_output(schema=TravelSegmentOptions)
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        workflow = StateGraph(
            input_schema=ItineraryAgentInput,
            state_schema=ItineraryState)

        (workflow
         .add_node('filter_places', self._filter_and_prioritize_places)
         .add_node('plan_themes', self._plan_daily_themes)
         .add_node('allocate_accommodation', self._allocate_accommodation)
         .add_node('build_daily_schedules', self._build_daily_schedules)
         .add_node('optimize_routes', self._optimize_routes)
         .add_node('calculate_travel_segments', self._calculate_travel_segments)
         .add_node('validate_budget_constraints', self._validate_budget_constraints)
         .add_node('generate_recommendations', self._generate_additional_recommendations)
         .add_node('finalize_itinerary', self._finalize_itinerary))

        (workflow
         .set_entry_point('filter_places')
         .add_edge('filter_places', 'plan_themes')
         .add_edge('plan_themes', 'allocate_accommodation')
         .add_edge('allocate_accommodation', 'build_daily_schedules')
         .add_edge('optimize_routes', 'calculate_travel_segments')
         .add_edge('build_daily_schedules', 'optimize_routes')
         .add_edge('calculate_travel_segments', 'validate_budget_constraints')
         .add_conditional_edges(
            'validate_budget_constraints',
            self._should_replan,
            {
                'replan': 'build_daily_schedules',
                'continue': 'generate_recommendations'
            }
        )
         .add_edge('generate_recommendations', 'finalize_itinerary')
         .set_finish_point('finalize_itinerary'))

    def _filter_and_prioritize_places(self, state: ItineraryState):
        self._logger.info("🔎 Filtering and prioritizing places")
        
        trip_request = state.trip_request
        destination_report = state.destination_report

        all_places = (
                destination_report.landmarks.report +
                destination_report.establishments.report +
                destination_report.events.report +
                destination_report.accommodations.report
        )

        state.selected_places = filter_places_by_criteria(all_places, trip_request)
        return state

    def _plan_daily_themes(self, state: ItineraryState) -> ItineraryState:
        """Plan themes for each day based on interests and selected places"""
        self._logger.info("❓ Generate themes for each day")
        
        trip_request = state.trip_request
        selected_places = state.selected_places

        # Use LLM to generate logical daily themes
        themes_prompt = f"""
        Plan {trip_request.total_days} daily themes for a trip to {trip_request.destination}.
        
        Trip details:
        {trip_request.format_for_llm()}
        
        Available places: {len(selected_places)} locations
        
        Create logical themes that:
        1. Group related activities/areas together
        2. Consider travel logistics (don't zigzag across the city)
        3. Balance must-see attractions with interests
        4. Account for opening hours and booking requirements
        
        Return only a list of theme names, one per day.
        """

        # This would use your LLM to generate themes
        daily_themes = self._generate_themes_with_llm(themes_prompt, trip_request.total_days)

        state.daily_themes = daily_themes
        return state

    def _generate_themes_with_llm(self, prompt: str, total_days: int) -> DailyThemes:
        
        try:
            response: DailyThemes = self.theme_llm.invoke(input=prompt)
            response.add_additional_themes_if_incomplete(required_num=total_days)
            return response
        except Exception:
            fallback_themes = [
                "Historic City Center", "Museums & Culture", "Local Neighborhoods",
                "Nature & Parks", "Food & Markets", "Hidden Gems", "Relaxation Day"
            ]
            return DailyThemes(list=(fallback_themes * ((total_days // len(fallback_themes)) + 1))[:total_days])

    def _allocate_accommodation(self, state: ItineraryState) -> ItineraryState:
        self._logger.info("🏨 Generating accommodation activities")
        
        trip_request = state.trip_request
        accommodations = [p for p in state.selected_places if isinstance(p, Accommodation)]

        selected_accommodation: Accommodation = select_best_accommodation(accommodations, trip_request)

        accommodation_activities: List[ItineraryActivity] = []
        current_date = trip_request.start_date

        while current_date < trip_request.end_date:
            activity = ItineraryActivity(
                place_id=selected_accommodation.id,
                activity_type=ActivityType.ACCOMMODATION,
                name=f"Stay at {selected_accommodation.name}",
                description="Overnight accommodation",
                start_time=datetime.combine(current_date, time(22, 0)),
                end_time=datetime.combine(current_date + timedelta(days=1), time(9, 0)),
                estimated_cost=min(selected_accommodation.price_options) / trip_request.travelers,
                coordinates=selected_accommodation.coordinates,
                booking_required=selected_accommodation.booking_type == BookingType.REQUIRED,
                booking_url=selected_accommodation.website
            )
            accommodation_activities.append(activity)
            current_date += timedelta(days=1)

        state.accommodation_activities = accommodation_activities
        return state

    def _build_daily_schedules(self, state: ItineraryState) -> ItineraryState:
        self._logger.info("📆 Building daily schedules")
        
        schedule_builder = ScheduleBuilder()

        state.daily_itineraries = schedule_builder.build(state.trip_request, state.selected_places, state.daily_themes)
        
        return state

    def _optimize_routes(self, state: ItineraryState) -> ItineraryState:
        """Optimize the order of activities within each day for minimal travel time"""
        self._logger.info('🗺️📌 Routing and optimizing activity order')
        
        for day_itinerary in state.daily_itineraries:
            activities_with_coords = [
                a for a in day_itinerary.activities if a.coordinates and a.activity_type != ActivityType.ACCOMMODATION
            ]
            
            if len(activities_with_coords) <= 2:
                continue

            optimized_activities = self._optimize_activity_order(activities_with_coords)

            # Replace the activities in the day
            other_activities = [
                a for a in day_itinerary.activities if not a.coordinates or a.activity_type == ActivityType.ACCOMMODATION
            ]

            day_itinerary.activities = optimized_activities + other_activities
            day_itinerary.activities.sort(key=lambda x: x.start_time)

        return state

    def _calculate_travel_segments(self, state: ItineraryState) -> ItineraryState:
        """Calculate travel time and cost between activities"""
        
        self._logger.info("🚶‍➡️ Calculating travel segments between activities")
        
        options = self._get_travel_segment_options()
        
        for day_itinerary in state.daily_itineraries:
            travel_segments: list[TravelSegment] = []
            activities = day_itinerary.activities

            for i in range(len(activities) - 1):
                current_activity = activities[i]
                next_activity = activities[i + 1]

                if current_activity.coordinates and next_activity.coordinates:
                    segment = calculate_travel_segment(current_activity, next_activity, options)
                    travel_segments.append(segment)

            day_itinerary.travel_segments = travel_segments

        return state

    def _get_travel_segment_options(self) -> TravelSegmentOptions:
        prompt = """
        Search for trusted sources on transport fares. Specifically:
        - The standard public transport fare (average for buses, metro, etc.)
        - The base taxi fare
        
        Convert all currencies to EUR.
        """
        
        self._logger.info("Searching for public transport fares")
        
        response = self.travel_segment_helper_llm.invoke(input=prompt)
        return response

    @staticmethod
    def _optimize_activity_order(activities: List[ItineraryActivity]) -> List[ItineraryActivity]:
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
            activity.end_time = current_time + timedelta(
                hours=next(p.typical_hours_of_stay for p in [] if p.id == activity.place_id),
            ) or timedelta(hours=2)
            current_time = activity.end_time + timedelta(minutes=30)  # Travel buffer

        return optimized

    