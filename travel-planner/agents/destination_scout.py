from langchain_core.language_models import BaseLanguageModel

from core import BaseAgent
from destination import DestinationReport, Event, Place, Landmark
from trip import TripRequest


class DestinationScoutAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel) -> None:
        super().__init__('destination_scout', llm.with_structured_output(schema=DestinationReport))

    def invoke(self, request: TripRequest) -> DestinationReport:
        self._logger.info('🚀 Invoked')

        landmarks = self._research_landmarks(request)
        food_highlights = self._research_food_highlights(request)
        events = self._research_events(request)
        additional_places = self._research_additional_places(request)

        return DestinationReport(
            landmarks=landmarks,
            food_highlights=food_highlights,
            events=events,
            additional_places=additional_places
        )

    def _research_landmarks(self, request: TripRequest) -> list[Landmark]:
        """ Find landmarks for the destination"""
        self._logger.info('🔎 Researching landmarks..')
        pass

    def _research_food_highlights(self, request: TripRequest) -> list[Place]:
        """Find places to eat"""
        self._logger.info('🔎 Researching places to eat..')
        pass

    def _research_events(self, request: TripRequest) -> list[Event]:
        """Find events within the trip dates, return a list of each event's name and pricing"""
        self._logger.info('🔎 Researching events for the trip dates..')
        pass

    def _research_additional_places(self, request: TripRequest) -> list[Place]:
        """Find additional places such as museums, parks and shops"""
        self._logger.info('🔎 Researching additional places to go..')
        pass
