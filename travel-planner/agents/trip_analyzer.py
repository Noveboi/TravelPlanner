from datetime import date
from typing import List

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from models.trip import TripRequest, TravelStyle

class TripAnalyzerAgent:
    def __init__(self, llm: BaseLanguageModel) -> None:
        self._llm = llm


    def _create_analysis_prompt(self, req: TripRequest) -> list[BaseMessage]:
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