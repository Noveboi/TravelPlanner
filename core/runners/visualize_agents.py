from langgraph.graph.state import CompiledStateGraph

import setup as base
from core.agents.places.accommodation_scout import AccommodationScoutAgent
from core.tools.foursquare import FoursquareApiClient


# noinspection PyUnresolvedReferences
def display_agent(agent: object) -> None:
    if not hasattr(agent, 'workflow') and not isinstance(agent.workflow, CompiledStateGraph):
        raise ValueError('Agent must have "workflow" field that is a compiled state graph')

    with open(f'{agent.__class__.__name__}.png', 'wb') as f:
        f.write(agent.workflow.get_graph().draw_mermaid_png())


ag = AccommodationScoutAgent(base.llm, FoursquareApiClient())

if __name__ == '__main__':
    pass
