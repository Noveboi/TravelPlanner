from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

import setup as base
from core.agents.itinerary.itinerary_agent import ItineraryBuilderAgent
from core.agents.places.accommodation_scout import AccommodationScoutAgent
from core.agents.places.establishment_scout import EstablishmentScoutAgent
from core.agents.places.landmark_scout import LandmarkScoutAgent
from core.models.places import AccommodationReport
from core.tools.foursquare import FoursquareApiClient
from core.tools.tools import get_available_tools
from core.utils import invoke_react_agent


# noinspection PyUnresolvedReferences
def display_agent(agent: object) -> None:
    if not hasattr(agent, 'workflow') and not isinstance(agent.workflow, CompiledStateGraph):
        raise ValueError('Agent must have "workflow" field that is a compiled state graph')

    with open(f'{agent.__class__.__name__}.png', 'wb') as f:
        f.write(agent.workflow.get_graph().draw_mermaid_png())

ag = AccommodationScoutAgent(base.llm, FoursquareApiClient())

if __name__ == '__main__':
    pass