from langchain_core.language_models import LanguageModelInput, BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from planner.models.places import EstablishmentReport
from planner.models.trip import TripRequest
from ..base import BaseAgent
from ...tools.tools import get_available_tools


class EstablishmentScoutAgent(BaseAgent):
    """
    Researches information about restaurants, cafés, bars and more...
    """

    def __init__(self, llm: BaseChatModel):
        super().__init__('establishment_scout')
        self._llm = llm.bind_tools(get_available_tools())
        self._structured_llm = llm.with_structured_output(schema=EstablishmentReport)

    def invoke(self, request: TripRequest) -> EstablishmentReport:
        self._logger.info("🔎 Researching establishments...")

        self._logger.info("Searching online...")
        search_prompt = self._create_search_prompt(request)
        search_results = self._llm.invoke(search_prompt)

        self._logger.info('Compiling search results into comprehensive list...')
        prompt = self._create_structured_prompt(request, search_results)
        response = self._structured_llm.invoke(prompt)
        
        assert isinstance(response, EstablishmentReport)
        
        return response

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
    def _create_structured_prompt(req: TripRequest, search_results: BaseMessage) -> LanguageModelInput:
        return [
            SystemMessage(content=f"""
            You are an expert travel agent and local {req.destination} guide. 
            Your speciality is establishments - restaurants, cafes, bars, any places where people can eat or drink.
            
            """, ),
            HumanMessage(content=f"""
            Use the following search results to generate a comprehensive and prioritized list of establishments based in {req.destination}:
            {search_results.content}
            
            Consider the following travel parameters when curating establishments:
            {req.format_for_llm()}
            """)
        ]
