import logging
from typing import TypeVar, Any, Type, cast, List

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from core.tools.tools import get_available_tools

log = logging.getLogger('app')
T = TypeVar('T')


def items_of_type(items: List[Any], t: Type[T]) -> List[T]:
    return [x for x in items if isinstance(x, t)]


def cast_items(items: List[Any], t: Type[T]) -> List[T]:
    # Only keep instances of t, then cast to satisfy the type checker
    return [cast(T, x) for x in items if isinstance(x, t)]


TOutput = TypeVar('TOutput', bound=BaseModel)


def invoke_react_agent(
        llm: Runnable,
        messages: List[BaseMessage],
        schema: Type[TOutput],
        tools: List[BaseTool] | None = None,
) -> TOutput:
    """Invoke a ReAct agent and return a structured response."""

    agent = create_react_agent(
        model=llm,
        tools=tools if tools is not None else get_available_tools(),
        response_format=schema,
    )

    handler = ToolLoggingHandler()

    # noinspection PyTypeChecker
    response: dict[str, Any] = agent.invoke(input={'messages': messages}, config={"callbacks": [handler]})

    structured_response: TOutput | None = response.get("structured_response")

    if structured_response is None:
        log.error("Agent did not return a structured response.")
        raise ValueError(f"Agent did not return a structured response. Dictionary had keys: {response.keys()}")

    return structured_response


class ToolLoggingHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        log.info(f"Tool started: {serialized.get('name')}({input_str})")

    def on_tool_end(self, output, **kwargs):
        log.info("Tool finished.")
