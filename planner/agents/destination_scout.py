from langchain_core.language_models import BaseLanguageModel, LanguageModelInput
from langchain_core.messages import SystemMessage, HumanMessage

from .base import BaseAgent
from planner.models.places import LandmarksReport, EstablishmentReport, EventsReport
from planner.models.trip import TripRequest


class EstablishmentScoutAgent(BaseAgent):
    """
    Researches information about restaurants, cafés, bars and more...
    """

    def __init__(self, llm: BaseLanguageModel):
        super().__init__('establishment_scout', llm)
        self._structured_llm = llm.with_structured_output(schema=EstablishmentReport)

    def invoke(self, request: TripRequest) -> EstablishmentReport:
        self._logger.info("🔎 Researching establishments...")

        self._logger.info("Searching online...")
        search_prompt = self._create_search_prompt(request)
        search_results = self._llm.invoke(search_prompt)

        self._logger.info('Compiling search results into comprehensive list...')
        prompt = self._create_structured_prompt(request, search_results)
        return self._structured_llm.invoke(prompt)

    @staticmethod
    def _create_search_prompt(req: TripRequest) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are a local guide in {req.destination} that specializes in finding information about establishments such
            as restaurants, cafes, bars, pubs, etc...
            
            Use the available search tools to find current information about establishment happening in {req.destination}.
                         
            If the traveler's request shows any preferences for specific types of establishments, then tailor your search
            to those preferences.
            """),

            HumanMessage(content=f"""
            Search for establishments in {req.destination}
            
            Focus on establishments that would appeal to these travelers:
            {req.format_for_llm()}
            
            If the traveller's request doesn't provide much information, then search for generally popular establishments.
            Establishments include restaurants, cafes, bars, pubs among others...
            """)
        ]

    @staticmethod
    def _create_structured_prompt(req: TripRequest, search_results: str) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are an expert travel agent and local {req.destination} guide. 
            Your speciality is establishments - restaurants, cafes, bars, any places where people can eat or drink.
            
            """, ),
            HumanMessage(content=f"""
            Generate a comprehensive and prioritized list of establishments based in {req.destination}.
            Search the web to find and curate establishments based on recent information.
            
            
            Consider the following travel parameters when curating establishments:
            {req.format_for_llm()}
            """)
        ]


class EventScoutAgent(BaseAgent):
    """
    Researches information on events (such as concerts and festivals) taking place during the duration of the user's stay. 
    """

    def __init__(self, llm: BaseLanguageModel):
        super().__init__('event_scout', llm)
        self._structured_llm = llm.with_structured_output(schema=EventsReport)

    def invoke(self, request: TripRequest) -> EventsReport:
        self._logger.info('🔎 Researching events at the time of the trip...')

        search_prompt = self._create_search_prompt(request)
        search_result = self._llm.invoke(search_prompt)

        structure_prompt = self._create_structure_prompt(request, search_result.content)
        return self._structured_llm.invoke(structure_prompt)

    @staticmethod
    def _create_search_prompt(req: TripRequest) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are a local guide in {req.destination} that specializes in finding information about events.
            
            Use the available search tools to find current information about events happening in {req.destination} 
            between {req.start_date} and {req.end_date}.
            
            Search for events that match the travelers' interests and preferences.
            """),
            HumanMessage(content=f"""
            Search for events taking place between {req.start_date} and {req.end_date} in {req.destination}.
            
            Focus on events that would appeal to these travelers:
            {req.format_for_llm()}
            
            Events include festivals, social, cultural & arts, sports, recreation, concerts, theatre, cinema, and more...
            Please search for multiple types of events and provide comprehensive information.
            """)
        ]

    @staticmethod
    def _create_structure_prompt(req: TripRequest, search_results: str) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are organizing event information for travelers visiting {req.destination}.
            Based on the search results provided, create a comprehensive and prioritized list of events.
            """),
            HumanMessage(content=f"""
            Based on these search results about events in {req.destination}:

            {search_results}

            Create a prioritized list of events for these travelers:
            {req.format_for_llm()}

            Focus on events happening between {req.start_date} and {req.end_date}.
            """)
        ]


class LandmarkScoutAgent(BaseAgent):
    """
    Researches landmarks for the user's destination.
    """

    def __init__(self, llm: BaseLanguageModel):
        super().__init__('landmark_scout', llm.with_structured_output(schema=LandmarksReport))

    def invoke(self, request: TripRequest) -> LandmarksReport:
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
