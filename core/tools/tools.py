from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch

from core.tools.geocoding import ForwardGeocodingTool
from core.tools.spherical_distance import DistanceTool


def get_available_tools() -> list[BaseTool]:
    return [
        TavilySearch(max_results=10),
        DistanceTool(),
        ForwardGeocodingTool()
    ]
