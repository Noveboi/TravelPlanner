import logging
from typing import TypeVar, Optional

from langchain_core.language_models import LanguageModelInput
from langchain_core.runnables import Runnable
from langsmith import RunTree
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class BaseAgent:
    """
    A simple base class for this project's agents. 
    """
    def __init__(self, name: str, llm: Optional[Runnable[LanguageModelInput, T]] = None) -> None:
        self._logger = logging.getLogger(name=name)
        
        if llm is not None:
            self._llm = llm.with_listeners(
                on_start=self._start_listener,
                on_end=self._end_listener,
                on_error=self._error_listener
            )
        
        self._logger.info('✅ Initialized')
        

    def _start_listener(self, tree: RunTree) -> None:
        self._logger.info(f"🤖 Agent Started at {tree.start_time}")
    
    def _end_listener(self, tree: RunTree) -> None:
        self._logger.info(f"🤖 Agent Finished at {tree.end_time}")
        
    def _error_listener(self, tree: RunTree) -> None:
        self._logger.error(f"🤖 Agent error: {tree.error}")