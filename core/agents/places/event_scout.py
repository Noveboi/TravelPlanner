from langchain_core.language_models import LanguageModelInput, BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from core.models.places import EventsReport
from core.models.trip import TripRequest
from core.tools.tools import get_available_tools
from ..base import BaseAgent
from ...utils import invoke_react_agent


class EventScoutAgent(BaseAgent):
    """
    Researches information on events (such as concerts and festivals) taking place during the duration of the user's stay. 
    """

    def __init__(self, llm: BaseChatModel):
        super().__init__('event_scout')
        self._llm = llm

    def invoke(self, req: TripRequest) -> EventsReport:
        self._log.info('🔎 Researching events at the time of the trip...')

        response = invoke_react_agent(
            llm=self._llm,
            messages=[
                HumanMessage(f"""
                Search for events taking place in {req.destination} between {req.start_date} and {req.end_date}.
                
                Focus on events that would appeal to these travelers:
                {req.format_for_llm()}
                
                Events include festivals, social, cultural & arts, sports, recreation, concerts, theatre, cinema, and more...
                Return a maximum of 15 of the most relevant events to the travelers.
                """)
                ],
            schema=EventsReport
        )

        return response
