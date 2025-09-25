from langchain_core.language_models import LanguageModelInput, BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from planner.models.places import EventsReport
from planner.models.trip import TripRequest
from ..base import BaseAgent
from ...tools.tools import get_available_tools


class EventScoutAgent(BaseAgent):
    """
    Researches information on events (such as concerts and festivals) taking place during the duration of the user's stay. 
    """

    def __init__(self, llm: BaseChatModel):
        super().__init__('event_scout')
        self._llm = llm.bind_tools(get_available_tools())
        self._structured_llm = llm.with_structured_output(schema=EventsReport)

    def invoke(self, request: TripRequest) -> EventsReport:
        self._logger.info('🔎 Researching events at the time of the trip...')

        search_prompt = self._create_search_prompt(request)
        search_result = self._llm.invoke(search_prompt)

        assert isinstance(search_result.content, str)

        structure_prompt = self._create_structure_prompt(request, search_result.content)
        response = self._structured_llm.invoke(structure_prompt)

        assert isinstance(response, EventsReport)

        return response

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
