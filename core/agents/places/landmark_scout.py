import operator
import uuid
from typing import Annotated, Any, Literal, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from core.models.places import LandmarksReport, Place, Priority, Landmark
from core.models.trip import TripRequest
from core.utils import invoke_react_agent
from .places_utils import to_json
from ..base import BaseAgent
from ..null_checks import require
from ..state import SearchInfo
from ...tools.foursquare import FoursquareApiClient, PlaceSearchRequest, FoursquarePlace, convert_fsq_to_place


class ImprovedLandmark(BaseModel):
    place_id: uuid.UUID = Field(description="The ID referencing the landmark")
    priority: Priority = Field(description='The importance of this landmark relevant to the request of the user')
    reason_to_go: str = Field(description='A brief reason why the user should go here. Keep it short')


class ImprovedLandmarks(BaseModel):
    list: List[ImprovedLandmark] = Field()


class LandmarksState(BaseModel):
    trip_request: TripRequest = Field()
    landmarks_to_retrieve: int = Field()
    landmarks: Annotated[list[Place], operator.add] = Field(
        description='A list of the currently collected landmarks',
        default_factory=list
    )
    improved_landmarks: ImprovedLandmarks | None = Field(default=None)
    report: LandmarksReport | None = Field(
        description='The final report',
        default=None
    )
    local_info: SearchInfo = Field()


class LandmarkScoutAgent(BaseAgent):
    """
    Researches landmarks for the user's destination.
    """

    def __init__(self, llm: BaseChatModel, client: FoursquareApiClient):
        super().__init__('landmark_scout')
        self._client = client
        self._llm = llm
        self.workflow = self._create_workflow().compile()

    def _create_workflow(self) -> StateGraph[LandmarksState, Any, LandmarksState]:
        workflow = StateGraph(
            input_schema=LandmarksState,
            state_schema=LandmarksState,
            output_schema=LandmarksState
        )

        workflow.add_node('expand_search_info', self._expand_search)
        workflow.add_node('search_landmarks', self._search_landmarks)
        workflow.add_node('polish_results', self._polish_results)
        workflow.add_node('generate_report', self._generate_report)

        workflow.set_entry_point('search_landmarks')
        workflow.add_conditional_edges(
            'search_landmarks',
            self._needs_more_landmarks,
            {
                'search_more_landmarks': 'expand_search_info',
                'ok': 'polish_results'
            }
        )

        workflow.add_edge('expand_search_info', 'search_landmarks')
        workflow.add_edge('polish_results', 'generate_report')
        workflow.set_finish_point('generate_report')

        return workflow

    def _polish_results(self, state: LandmarksState) -> LandmarksState:
        self._log.info('🏞️ Polishing search results for landmarks')

        candidate_places = [p.model_dump_json() for p in state.landmarks]
        trip_ctx = require(state.trip_request).model_dump_json()

        system = (
            f"You are an expert travel agent in {state.trip_request.destination}. "
            "Given a list of candidate landmarks for a destination, return a polished, deduplicated, and prioritized "
            "list of top landmarks. Your response should reference the landmarks by their ID (UUID)."
        )

        user = {
            "user_trip_request": trip_ctx,
            "candidates": candidate_places,
            "instructions": {
                "max_results": state.landmarks_to_retrieve,
                "priority_guidance": "Assign priority as one of [4,3,2,1] corresponding to [ESSENTIAL,HIGH,MEDIUM,LOW]."
            }
        }

        response = invoke_react_agent(
            self._llm,
            messages=[HumanMessage(to_json(user))],
            schema=ImprovedLandmarks,
            system_message=SystemMessage(system))

        state.improved_landmarks = response

        return state

    def _generate_report(self, state: LandmarksState) -> LandmarksState:
        self._log.info('📃 Generating landmark report...')

        by_id = {place.id: place for place in state.landmarks}
        landmarks = [
            Landmark(**require(by_id.get(improved.place_id)).model_dump() | improved.model_dump())
            for improved in require(state.improved_landmarks).list
        ]

        state.report = LandmarksReport(report=landmarks)

        return state

    @staticmethod
    def _needs_more_landmarks(state: LandmarksState) -> Literal['search_more_landmarks', 'ok']:
        return 'search_more_landmarks' if len(state.landmarks) < 50 else 'ok'

    def _search_landmarks(self, state: LandmarksState) -> dict[str, list[Place]]:
        self._log.info('🔎 Searching for landmarks...')

        req = PlaceSearchRequest(
            center=require(state.local_info).center,
            radius=require(state.local_info).radius,
            limit=state.landmarks_to_retrieve,
            query='landmarks'
        )

        fsq_places: list[FoursquarePlace] = require(self._client.search(req)).results
        places: list[Place] = [convert_fsq_to_place(p) for p in fsq_places]

        return {'landmarks': places}

    def _expand_search(self, state: LandmarksState) -> LandmarksState:
        self._log.info('Expanding search...')
        state.local_info = state.local_info.expand_radius(10_000)
        return state

    def invoke(self, request: TripRequest, info: SearchInfo) -> LandmarksReport:
        self._log.info('🔎 Researching landmarks...')

        initial_state = LandmarksState(
            trip_request=request,
            local_info=info,
            landmarks_to_retrieve=min(50, request.total_days * 6),
        )

        final_state = self.workflow.invoke(input=initial_state)
        report = final_state['report']

        assert isinstance(report, LandmarksReport)

        return report
