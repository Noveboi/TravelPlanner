from typing import Any, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch

def get_available_tools() -> list[BaseTool]:
    return [
        TavilySearch(max_results=10)
    ]

def bind_necessary_tools(llm: BaseChatModel) -> Runnable[PromptValue | str | Sequence[BaseMessage | list[str] | tuple[str, str] | str | dict[str, Any]], BaseMessage]:
    return llm.bind_tools(get_available_tools())