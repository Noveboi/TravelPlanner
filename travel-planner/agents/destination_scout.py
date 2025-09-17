from langchain_core.language_models import BaseLanguageModel

from destination import DestinationReport

from core import BaseAgent

class DestinationScoutAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel) -> None:
        super().__init__('destination_scout', llm.with_structured_output(schema=DestinationReport))