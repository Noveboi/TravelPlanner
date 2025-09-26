from typing import Self

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from core.models.geography import Coordinates
from core.models.trip import TripRequest
from core.tools.tools import get_available_tools


class SearchInfo(BaseModel):
    center: Coordinates = Field(default=Coordinates(0, 0))
    radius: int = Field(ge=0, le=100_000, default=0)
    
    def expand_radius(self, increment: int) -> Self:
        return SearchInfo(
            center=self.center,
            radius=min(100_000, self.radius + increment)
        )

def determine_search(req: TripRequest, llm: Runnable) -> SearchInfo:
    min_radius = 7_500
    
    prompt = f"""
    You are selecting a geographic search circle for downstream place discovery. The destination is "{req.destination}".
    
    Inputs:
    {req.format_for_llm()}

    Task:
    - Choose a center (latitude, longitude) and a radius (meters) that best covers key points of interest for the trip.
    - Prefer centroids near the main tourist/transport hubs of the destination.
    
    Constraints:
    - Radius must be >= {min_radius} meters
    - Consider trip duration: shorter trips → tighter radius near dense attractions; longer trips → broader radius.
    """

    agent = create_react_agent(
        model=llm,
        tools=get_available_tools(),
        response_format=SearchInfo,
    )

    # noinspection PyTypeChecker
    response = agent.invoke(input={'messages': [HumanMessage(content=prompt)]})
    structured_response = response['structured_response']
    
    assert isinstance(structured_response, SearchInfo)
    
    return structured_response
