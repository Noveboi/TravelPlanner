from typing import cast
import logging

from langchain_core.runnables import Runnable
from langchain_core.language_models import BaseLanguageModel, LanguageModelInput
from langchain_core.messages import SystemMessage, HumanMessage
from trip import TripProfile, TripRequest

class TripAnalyzerAgent:
    def __init__(self, llm: BaseLanguageModel) -> None:
        self._logger = logging.getLogger(name='trip_analyzer')

        self._logger.info('Initializing')
        structured_llm = llm.with_structured_output(schema=TripProfile)

        # We do a cast here because `with_structured_output` does not return a proper type assignable to the desired.
        self._llm: Runnable[LanguageModelInput, TripProfile] = cast(
            Runnable[LanguageModelInput, TripProfile],
            structured_llm
        )

        self._logger.info('Initialized')

    def invoke(self, request: TripRequest) -> TripProfile:
        self._logger.info('Invoked')
        prompt = self._create_analysis_prompt(request)
        return self._llm.invoke(prompt)


    def _create_analysis_prompt(self, req: TripRequest) -> LanguageModelInput:
        duration = req.duration
        daily_budget = req.budget / duration if duration > 0 else req.budget
        
        return [
            SystemMessage(content="""
            You are a travel psychology expert. Analyze the user's trip request and provide insights about:
            1. Travel Personality: What their choices reveal about their travel style and preferences
            2. Group Dynamics: How the group size and type might influence the trip
            3. Budget Considerations: Whether their budget aligns with their expectations
            4. Time Management: How well their duration matches their interests
            5. Recommendations: Specific suggestions to enhance their travel experience
            
            Provide concise, actionable insights that will help personalize their trip.
                          
            Information about the structured output:
            - The "preferred_activities" field is a list of general activities based on the trip request's data. Examples
            of preferred activities include: Sightseeing, Museums, Concerts, Leisure, Workshops, Hiking, Luxury Dining, Cozy Dining, etc...
            - The "group_focus" field is a list of keywords that describe what the group should focus on based on the type of group.
            For example, a "Couple" group type could focus on Romance and Atmosphere, while a "Family" group type could focus a Fun for all ages and Safety
            - The "group_recommendations" field is a list of activities/places that the group can do/go to. 
            - The "time_allocation" field allocates a weight to each activity found you've added in "preferred_activities" and "group_recommendations".
            The bigger the weight, the more time should be allocated to that activity.
            - The "key_recommendations" field contains your best/top recommendations to enhance the trip experience.
            - The "potential_challenges" field contains issues or problems that might arise that the user needs to be made aware of.
            Potential challenges can be budget limitations or location-specific issues.
            """),
            HumanMessage(content=f"""
            Analyze this trip request:
            Destination: {req.destination}
            Duration: {duration} days ({req.start_date} to {req.end_date})
            Budget: ${req.budget:,.2f} EUR (approximately ${daily_budget:,.2f} per day)
            Group: {req.travelers} travelers - {req.trip_type.value.title()} trip
            Travel Style(s): {req.format_travel_styles()}
            Interests: {req.format_interests()}
            
            Please provide a comprehensive analysis based on the above criteria.
            """)]