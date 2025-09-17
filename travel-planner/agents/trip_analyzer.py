import logging
from typing import cast

from langchain_core.language_models import BaseLanguageModel, LanguageModelInput
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import Runnable

from .trip import GeneralTripAnalysis, TripRequest


class TripAnalyzerAgent:
    def __init__(self, llm: BaseLanguageModel) -> None:
        self._logger = logging.getLogger(name='trip_analyzer')

        self._logger.info('Initializing')
        structured_llm = llm.with_structured_output(schema=GeneralTripAnalysis)

        # We do a cast here because `with_structured_output` does not return a proper type assignable to the desired.
        self._llm: Runnable[LanguageModelInput, GeneralTripAnalysis] = cast(
            Runnable[LanguageModelInput, GeneralTripAnalysis],
            structured_llm
        )

        self._logger.info('Initialized')

    def invoke(self, request: TripRequest) -> GeneralTripAnalysis:
        self._logger.info('Invoked')
        prompt = self._create_analysis_prompt(request)
        return self._llm.invoke(prompt)

    @staticmethod
    def _create_analysis_prompt(req: TripRequest) -> LanguageModelInput:
        duration = req.duration

        return [
            SystemMessage(content="""
            You are a travel psychology expert. Analyze the user's trip request and provide insights about:
            1. Travel Personality: What their choices reveal about their travel style and preferences
            2. Group Dynamics: How the group size and type might influence the trip
            3. Budget Considerations: Whether their budget aligns with their expectations
            4. Time Management: How well their duration matches their interests
            5. Recommendations: Specific suggestions to enhance their travel experience
            
            Provide actionable insights that will help personalize their trip.
            Do not provide any information on specific places.
                          
            Information about the structured output:
            - The "group_focus" field is a list of keywords that describe what the group should focus on based on the type of group.
            - The "group_recommendations" field is a list of activities that the group can do. 
            - The "key_recommendations" field contains your best/top recommendations to enhance the trip experience.
            - The "potential_challenges" field contains issues or problems that might arise that the user needs to be made aware of. Potential challenges can be budget limitations or location-specific issues.
            """),
            HumanMessage(content=f"""
            Analyze this trip request:
            - Destination: {req.destination}
            - Duration: {duration} days ({req.start_date} to {req.end_date})
            - Budget: ${req.budget:,.2f} EUR
            - Group: {req.travelers} travelers - '{req.trip_type.value.title()}' trip
            - Travel Style(s): {req.format_travel_styles()}
            - Interests: {req.format_interests()}
            
            Please provide a comprehensive analysis based on the above criteria.
            """)]
