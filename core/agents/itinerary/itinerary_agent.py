from typing import List, Optional, Any

from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.itinerary.accommodation_choice import select_best_accommodation
from core.agents.itinerary.budget import validate_budget, BudgetTracker, create_budget_breakdown
from core.agents.itinerary.day_itinerary_builder import ScheduleBuilder
from core.agents.itinerary.themes import DailyThemes, generate_daily_themes
from core.agents.null_checks import require
from core.models.itinerary import DayItinerary, TripItinerary
from core.models.places import DestinationReport, Place, Accommodation
from core.models.trip import TripRequest


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
    selected_places: List[Place] | None = Field(
        description="A list of filtered and prioritized places, curated algorithmically",
        default=None
    )
    daily_themes: DailyThemes | None = Field(default=None)
    accommodation: Accommodation | None = Field(
        description="The accommodation that the traveller will reside in.",
        default=None
    )
    daily_itineraries: List[DayItinerary] = Field(
        description="An itinerary for each day of the trip",
        default_factory=list
    )
    final_itinerary: Optional[TripItinerary] = Field(
        description="The final itinerary containing all the relevant information",
        default=None
    )
    budget_tracker: Optional[BudgetTracker] = Field(
        description="A budget tracker for ensuring we do not go over-budget",
        default=None
    )
    errors: List[str] = Field(
        description="A list of errors for unexpected scenarios",
        default_factory=list
    )


class ItineraryBuilderAgent(BaseAgent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(name='itinerary_builder')
        self.workflow = self._create_workflow().compile()
        self._llm = llm

    def invoke(self, request: TripRequest, destination_report: DestinationReport) -> TripItinerary:
        final_state = self.workflow.invoke(
            input=ItineraryAgentInput(trip_request=request, destination_report=destination_report)
        )

        return final_state['final_itinerary']

    def _create_workflow(self) -> StateGraph[ItineraryState, Any, ItineraryAgentInput, Any]:
        workflow = StateGraph(
            input_schema=ItineraryAgentInput,
            state_schema=ItineraryState
        )

        (workflow
         .add_node('plan_themes', self._plan_daily_themes)
         .add_node('allocate_accommodation', self._allocate_accommodation)
         .add_node('build_daily_schedules', self._build_daily_schedules)
         # .add_node('optimize_routes', self._optimize_routes)
         .add_node('validate_budget_constraints', self._validate_budget_constraints)
         .add_node('finalize_itinerary', self._finalize_itinerary))

        (workflow
         .set_entry_point('plan_themes')
         .add_edge('plan_themes', 'allocate_accommodation')
         .add_edge('allocate_accommodation', 'build_daily_schedules')
         .add_edge('build_daily_schedules', 'validate_budget_constraints')
         # .add_edge('build_daily_schedules', 'optimize_routes')
         # .add_edge('optimize_routes', 'validate_budget_constraints')
         .add_conditional_edges(
            'validate_budget_constraints',
            self._should_replan,
            {
                'replan': 'build_daily_schedules',
                'continue': 'finalize_itinerary'
            }
        )
         .set_finish_point('finalize_itinerary'))

        return workflow

    def _plan_daily_themes(self, state: ItineraryState) -> ItineraryState:
        """Plan themes for each day based on interests and selected places"""
        self._log.info("❓ Generate themes for each day")

        state.daily_themes = generate_daily_themes(
            self._llm,
            state.trip_request,
            require(state.selected_places))

        return state

    def _allocate_accommodation(self, state: ItineraryState) -> ItineraryState:
        self._log.info("🏨 Generating accommodation activities")

        trip_request: TripRequest = state.trip_request
        accommodations = state.destination_report.accommodations.report

        state.accommodation = select_best_accommodation(accommodations, trip_request)
        return state

    def _build_daily_schedules(self, state: ItineraryState) -> ItineraryState:
        self._log.info("📆 Building daily schedules")

        schedule_builder = ScheduleBuilder(self._llm)

        state.daily_itineraries = schedule_builder.build(
            state.trip_request,
            require(state.selected_places),
            require(state.daily_themes))

        return state

    # def _optimize_routes(self, state: ItineraryState) -> ItineraryState:
    #     """Optimize the order of activities within each day for minimal travel time"""
    #     self._log.info('🗺️📌 Routing and optimizing activity order')
    # 
    #     for day_itinerary in state.daily_itineraries:
    #         activities_with_coordinates = [a for a in day_itinerary.activities if a.coordinates is not None]
    # 
    #         if len(activities_with_coordinates) <= 2:
    #             continue
    # 
    #         optimized_activities = optimize_activity_order(
    #             activities_with_coordinates,
    #             require(state.selected_places))
    # 
    #         # Replace the activities in the day
    #         other_activities = [a for a in day_itinerary.activities if a.coordinates is None]
    # 
    #         day_itinerary.activities = optimized_activities + other_activities
    #         day_itinerary.activities.sort(key=lambda x: x.start_time)
    # 
    #     return state

    def _validate_budget_constraints(self, state: ItineraryState) -> ItineraryState:
        self._log.info("💵 Validating budget constraints")

        budget_tracker = validate_budget(state.trip_request, state.daily_itineraries)
        state.budget_tracker = budget_tracker
        return state

    def _finalize_itinerary(self, state: ItineraryState) -> ItineraryState:
        """Create the final itinerary object"""
        self._log.info('Creating the final itinerary')

        trip_request = state.trip_request

        state.final_itinerary = TripItinerary(
            destination=trip_request.destination,
            start_date=trip_request.start_date,
            end_date=trip_request.end_date,
            total_days=(trip_request.end_date - trip_request.start_date).days + 1,
            daily_itineraries=state.daily_itineraries,
            accommodation=require(state.accommodation),
            budget_breakdown=create_budget_breakdown(require(state.accommodation), state.daily_itineraries,
                                                     trip_request.travelers),
        )

        return state

    def _should_replan(self, state: ItineraryState) -> str:
        """Decide whether to replan based on budget validation"""

        if require(state.budget_tracker).is_over_budget:
            self._log.warning('Overshot budget with current itinerary, retrying...')
            return 'replan'
        else:
            self._log.info('Within budget limits, continuing...')
            return 'continue'
