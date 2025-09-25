from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch


def get_available_tools() -> list[BaseTool]:
    return [
        TavilySearch(max_results=10)
    ]
