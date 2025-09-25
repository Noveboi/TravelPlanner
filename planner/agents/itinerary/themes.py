from typing import List

from langchain_core.language_models import BaseLanguageModel
from pydantic import BaseModel, Field

from planner.models.places import Place
from planner.models.trip import TripRequest


class DailyThemes(BaseModel):
    list: List[str] = Field(description="A list containing a theme for each day of the trip")

    def add_additional_themes_if_incomplete(self, required_num: int) -> None:
        self.list.extend([f"Exploration Day {i + 1}" for i in range(len(list), required_num)])

def generate_daily_themes(llm: BaseLanguageModel, request: TripRequest, places: list[Place]) -> DailyThemes:
    def _generate_themes_with_llm(prompt: str, total_days: int) -> DailyThemes:
        theme_llm = llm.with_structured_output(schema=DailyThemes)
        
        try:
            response: DailyThemes = theme_llm.invoke(input=prompt)
            response.add_additional_themes_if_incomplete(required_num=total_days)
            return response
        except Exception:
            fallback_themes = [
                "Historic City Center", "Museums & Culture", "Local Neighborhoods",
                "Nature & Parks", "Food & Markets", "Hidden Gems", "Relaxation Day"
            ]
            return DailyThemes(list=(fallback_themes * ((total_days // len(fallback_themes)) + 1))[:total_days])


    # Use LLM to generate logical daily themes
    themes_prompt = f"""
        Plan {request.total_days} daily themes for a trip to {request.destination}.
        
        Trip details:
        {request.format_for_llm()}
        
        Available places: {len(places)} locations
        
        Create logical themes that:
        1. Group related activities/areas together
        2. Consider travel logistics (don't zigzag across the city)
        3. Balance must-see attractions with interests
        4. Account for opening hours and booking requirements
        
        Return only a list of theme names, one per day.
        """

    return _generate_themes_with_llm(themes_prompt, request.total_days)