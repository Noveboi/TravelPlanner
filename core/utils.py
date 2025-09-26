import logging
from typing import TypeVar, Any, Type, cast, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from tenacity import RetryCallState

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
        messages: List[HumanMessage],
        schema: Type[TOutput],
        system_message: SystemMessage | None = None,
        tools: List[BaseTool] | None = None,
) -> TOutput:
    """Invoke a ReAct agent and return a structured response."""

    static_prompt = f"""
                    {system_message.content if system_message else ''}
                    
                    Tips:
                    - Use the "forward geocoding" tool to find coordinates for places. If you are having trouble (3 or more tries) 
                    getting the coordinates for a place, then resort to searching the web for the coordinates
                    """

    agent = create_react_agent(
        model=llm,
        tools=tools if tools is not None else get_available_tools(),
        response_format=schema,
        prompt=static_prompt
    )

    handler = LoggingHandler()
    attempts = 1
    
    while attempts <= 3:
        try:
            # noinspection PyTypeChecker
            response: dict[str, Any] = agent.invoke(
                input={'messages': messages},
                config={
                    "callbacks": [handler],
                    "recursion_limit": 100
                })
    
            structured_response: TOutput | None = response.get("structured_response")
        
            if structured_response is None:
                log.error("Agent did not return a structured response.")
                raise ValueError(f"Agent did not return a structured response. Dictionary had keys: {response.keys()}")
        
            return structured_response
        except ValueError as e:
            message = str(e)
            log.error(f'❌ ReAct agent error: {message}')
            attempts += 1
            
            if "does not have a 'parsed' field nor a 'refusal' field" in message:
                log.error('❌ LLM refused to fulfill our request but did not specify why. Retrying the request')
                continue
            
            raise e
        
    raise RuntimeError('Ran out of attempts')


class LoggingHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, run_id, **kwargs):
        log.info(f"Tool '{run_id}' started: {serialized.get('name')}({input_str})")

    def on_tool_end(self, output, run_id, **kwargs):
        log.info(f"Tool '{run_id}' finished.")

    def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        log.error("❌ Tool '{run_id}' error occured", exc_info=error)

    def on_retry(
            self,
            retry_state: RetryCallState,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        log.info(f"Retrying '{run_id}' (Attempt #{retry_state.attempt_number}) (ACTION: {retry_state.next_action})")
