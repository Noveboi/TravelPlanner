from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from agents.base import BaseAgent
from agents.places.accommodation_scout import AccommodationScoutAgent
from agents.places.establishment_scout import EstablishmentScoutAgent
from agents.places.event_scout import EventScoutAgent
from agents.places.landmark_scout import LandmarkScoutAgent
from models import DestinationReport, LandmarksReport, EstablishmentReport, EventsReport, \
    AccommodationReport
from models import TripRequest
from tools import FoursquareApiClient


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

    def __init__(self, llm: BaseChatModel, client: FoursquareApiClient):
        super().__init__(name='destination_scout')
        self._client = client
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

        final_state = self.workflow.invoke(input=initial_state)

        return DestinationReport(
            landmarks=final_state['landmarks'],
            establishments=final_state['establishments'],
            events=final_state['events'],
            accommodations=final_state['accommodations']
        )

    def _create_workflow(self) -> StateGraph[DestinationState, Any, DestinationState, DestinationState]:
        workflow = StateGraph(
            state_schema=DestinationState,
            input_schema=DestinationState,
            output_schema=DestinationState)

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

    def _research_landmarks(self, state: DestinationState) -> dict[str, LandmarksReport]:
        scout = LandmarkScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        self._logger.info('✅ Finished Landmarks')

        return {'landmarks': result}

    def _research_events(self, state: DestinationState) -> dict[str, EventsReport]:
        scout = EventScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        self._logger.info('✅ Finished Events')

        return {'events': result}

    def _research_establishments(self, state: DestinationState) -> dict[str, EstablishmentReport]:
        scout = EstablishmentScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        self._logger.info('✅ Finished Establishments')

        return {'establishments': result}

    def _research_accommodations(self, state: DestinationState) -> dict[str, AccommodationReport]:
        scout = AccommodationScoutAgent(self._llm, self._client)
        result = scout.invoke(state.trip_request)

        self._logger.info('✅ Finished Accommodations')

        return {'accommodations': result}
