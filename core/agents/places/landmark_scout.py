from langchain_core.language_models import LanguageModelInput, BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from core.models.places import LandmarksReport
from core.models.trip import TripRequest
from ..base import BaseAgent


class LandmarkScoutAgent(BaseAgent):
    """
    Researches landmarks for the user's destination.
    """

    def __init__(self, llm: BaseChatModel):
        super().__init__('landmark_scout')
        self._llm = llm.with_structured_output(schema=LandmarksReport)

    def invoke(self, request: TripRequest) -> LandmarksReport:
        self._log.info('🔎 Researching landmarks...')

        prompt = self._create_prompt(request)
        response = self._llm.invoke(prompt)

        assert isinstance(response, LandmarksReport)

        self._log.info(f'Found {len(response.report)} landmarks')

        return response

    @staticmethod
    def _create_prompt(req: TripRequest) -> LanguageModelInput:
        return [
            SystemMessage(content="""
            You are an expert travel agent specializing in recommending which landmarks to visit for a specific destination.
            
            You can optionally search the web if you need up-to-date information on some landmarks.
            
            Give each landmark a priority using the "priority" field of your structured output.
            
            Provide a quick reason why the user should see each landmark using the "reason_to_go" field of your structured output
            """),
            HumanMessage(content=f"""
            Provide a comprehensive and prioritized list of the top landmarks for {req.destination}.
            
            Consider the following travel parameters when deciding:
            {req.format_for_llm()}
            
            Find and return a minimum of {min(req.total_days * 3, 30)}
            """)
        ]
