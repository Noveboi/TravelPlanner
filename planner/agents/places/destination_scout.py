from langchain_core.language_models import BaseLanguageModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from planner.agents.base import BaseAgent
from planner.agents.places.establishment_scout import EstablishmentScoutAgent
from planner.agents.places.event_scout import EventScoutAgent
from planner.agents.places.landmark_scout import LandmarkScoutAgent
from planner.models.places import DestinationReport, LandmarksReport, EstablishmentReport, EventsReport, \
    AccommodationReport
from planner.models.trip import TripRequest


class DestinationState(BaseModel):
    trip_request: TripRequest
    landmarks: LandmarksReport = Field()
    establishments: EstablishmentReport = Field()
    events: EventsReport = Field()
    accommodations: AccommodationReport = Field()


class DestinationScoutAgent(BaseAgent):
    """
    Agent that composes other scout agents and executes them in parallel (https://langchain-ai.github.io/langgraph/tutorials/workflows/#parallelization)
    """

    def __init__(self, llm: BaseLanguageModel):
        super().__init__(name='destination_scout')
        self._llm = llm
        self.workflow = self._create_workflow().compile()

    def invoke(self, request: TripRequest) -> DestinationReport:
        initial_state = DestinationState(
            trip_request=request,
            landmarks=LandmarksReport(report=[]),
            establishments=EstablishmentReport(report=[]),
            events=EventsReport(report=[]),
            accommodations=AccommodationReport(report=[]),
        )

        final_state: DestinationState = self.workflow.invoke(input=initial_state)

        return DestinationReport(
            landmarks=final_state.landmarks,
            establishments=final_state.establishments,
            events=final_state.events,
            accommodations=final_state.accommodations
        )

    def _create_workflow(self) -> StateGraph[DestinationState]:
        workflow: StateGraph[DestinationState] = StateGraph(state_schema=DestinationState)

        workflow.add_node('landmarks', self._research_landmarks)
        workflow.add_node('events', self._research_events)
        workflow.add_node('establishments', self._research_establishments)
        workflow.add_node('accommodations', self._research_accommodations)

        workflow.add_edge(START, 'landmarks')
        workflow.add_edge(START, 'events')
        workflow.add_edge(START, 'establishments')
        workflow.add_edge(START, 'accommodations')
        workflow.add_edge('landmarks', END)
        workflow.add_edge('events', END)
        workflow.add_edge('establishments', END)
        workflow.add_edge('accommodations', END)

        return workflow

    def _research_landmarks(self, state: DestinationState) -> DestinationState:
        scout = LandmarkScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        state.report.landmarks = result

        return state

    def _research_events(self, state: DestinationState) -> DestinationState:
        scout = EventScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        state.report.events = result

        return state

    def _research_establishments(self, state: DestinationState) -> DestinationState:
        scout = EstablishmentScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        state.report.establishments = result

        return state

    def _research_accommodations(self, state: DestinationState) -> DestinationState:
        scout = EstablishmentScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        state.report.accommodations = result

        return state
