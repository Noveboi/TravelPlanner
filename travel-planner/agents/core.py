import logging
from typing import TypeVar

from langchain_core.language_models import LanguageModelInput
from langchain_core.runnables import Runnable
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class BaseAgent:
    def __init__(self, name: str, llm: Runnable[LanguageModelInput, T]) -> None:
        self._logger = logging.getLogger(name=name)
        self._llm = llm
        self._logger.info('✅ Initialized')
