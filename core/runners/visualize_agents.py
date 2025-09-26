from IPython.display import Image, display
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

import core.runners.setup as x
from core.tools.tools import get_available_tools


class Test(BaseModel):
    nombre: int = Field()


agent_plain = create_react_agent(x.llm, tools=[])
agent_with_tools = create_react_agent(x.llm, tools=get_available_tools())
agent_with_output = create_react_agent(x.llm, response_format=Test, tools=[])

if __name__ == '__main__':
    display(Image(agent_plain.get_graph().draw_mermaid_png(max_retries=5)))
