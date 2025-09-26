from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch

from core.tools.geocoding import GlobalThrottledGeocodingTool
from core.tools.spherical_distance import DistanceTool

geo_tool = GlobalThrottledGeocodingTool()


def get_available_tools() -> list[BaseTool]:
    return [
        TavilySearch(max_results=10),
        DistanceTool(),
        geo_tool,
    ]
