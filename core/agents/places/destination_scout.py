from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.constants import END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.places.accommodation_scout import AccommodationScoutAgent
from core.agents.places.establishment_scout import EstablishmentScoutAgent
from core.agents.places.event_scout import EventScoutAgent
from core.agents.places.landmark_scout import LandmarkScoutAgent
from core.agents.state import SearchInfo, determine_search
from core.models.places import DestinationReport, LandmarksReport, EstablishmentReport, EventsReport, \
    AccommodationReport
from core.models.trip import TripRequest
from core.tools.foursquare import FoursquareApiClient


class DestinationState(BaseModel):
    trip_request: TripRequest
    landmarks: LandmarksReport = Field()
    establishments: EstablishmentReport = Field()
    events: EventsReport = Field()
    accommodations: AccommodationReport = Field()
    info: SearchInfo = Field()


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
            info=SearchInfo()
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

        workflow.add_node('get_search_info', self._get_search_info)
        workflow.add_node('landmarks', self._research_landmarks)
        workflow.add_node('events', self._research_events)
        workflow.add_node('establishments', self._research_establishments)
        workflow.add_node('accommodations', self._research_accommodations)

        workflow.set_entry_point('get_search_info')

        workflow.add_edge('get_search_info', 'landmarks')
        workflow.add_edge('get_search_info', 'events')
        workflow.add_edge('get_search_info', 'establishments')
        workflow.add_edge('get_search_info', 'accommodations')
        workflow.add_edge('landmarks', END)
        workflow.add_edge('events', END)
        workflow.add_edge('establishments', END)
        workflow.add_edge('accommodations', END)

        return workflow

    def _get_search_info(self, state: DestinationState) -> dict[str, SearchInfo]:
        self._log.info('🔎 Getting search info...')

        info = determine_search(state.trip_request, self._llm)

        self._log.info(f'🔎 Got search info: R = {info.radius}, LL = {info.center.to_string()}')

        return {'info': info}

    def _research_landmarks(self, state: DestinationState) -> dict[str, LandmarksReport]:
        scout = LandmarkScoutAgent(self._llm, self._client)
        result = scout.invoke(state.trip_request, state.info)

        self._log.info(f'✅ Finished Landmarks (found {len(result.report)})')

        return {'landmarks': result}

    def _research_events(self, state: DestinationState) -> dict[str, EventsReport]:
        scout = EventScoutAgent(self._llm)
        result = scout.invoke(state.trip_request)

        self._log.info(f'✅ Finished Events (found {len(result.report)})')

        return {'events': result}

    def _research_establishments(self, state: DestinationState) -> dict[str, EstablishmentReport]:
        scout = EstablishmentScoutAgent(self._llm, self._client)
        result = scout.invoke(state.trip_request, state.info)

        self._log.info(f'✅ Finished Establishments (found {len(result.report)})')

        return {'establishments': result}

    def _research_accommodations(self, state: DestinationState) -> dict[str, AccommodationReport]:
        scout = AccommodationScoutAgent(self._llm, self._client)
        result = scout.invoke(state.trip_request, state.info)

        self._log.info(f'✅ Finished Accommodations (found {len(result.report)})')

        return {'accommodations': result}
