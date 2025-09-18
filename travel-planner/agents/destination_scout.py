from langchain_core.language_models import BaseLanguageModel, LanguageModelInput
from langchain_core.messages import SystemMessage, HumanMessage

from .core import BaseAgent
from .destination import DestinationReport, Event, Place, Landmark, LandmarksReport, EstablishmentReport
from .trip import TripRequest


class DestinationScoutAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel) -> None:
        super().__init__('destination_scout', llm)

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

class EstablishmentScoutAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__('establishment_scout', llm.with_structured_output(schema=EstablishmentReport))
        
    def invoke(self, request: TripRequest) -> EstablishmentReport:
        """Find places to go eat, drink and relax"""
        self._logger.info("🔎 Researching establishments...")
        
        prompt = self._create_prompt(request)
        return self._llm.invoke(prompt)
    
    @staticmethod
    def _create_prompt(req: TripRequest) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are an expert travel agent and local {req.destination} guide. 
            Your speciality is establishments - restaurants, cafes, bars, any places where people can eat or drink.
            
            """,),
            HumanMessage(content=f"""
            Generate a comprehensive and prioritized list of establishments based in {req.destination}.
            Search the web to find and curate establishments based on recent information.
            
            Consider the following travel parameters when curating establishments:
            {req.format_for_llm()}
            """)
        ]

class LandmarkScoutAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__('landmark_scout', llm.with_structured_output(schema=LandmarksReport))

    def invoke(self, request: TripRequest) -> LandmarksReport:
        """ Find landmarks for the destination"""
        self._logger.info('🔎 Researching landmarks...')

        prompt = self._create_prompt(request)
        return self._llm.invoke(prompt)

    @staticmethod
    def _create_prompt(req: TripRequest) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are an expert travel agent specializing in recommending which landmarks to visit for a specific destination.
            
            You can optionally search the web if you need up-to-date information on some landmarks.
            Give each landmark a priority using the "priority" field of your structured output.
            Provide a quick reason why the user should see each landmark using the "reason_to_go" field of your structured output
            """),
            HumanMessage(content=f"""
            Provide a comprehensive and prioritized list of the top landmarks for {req.destination}.
            
            Consider the following travel parameters when deciding:
            {req.format_for_llm()}
            """)
        ]
