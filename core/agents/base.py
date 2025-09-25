import logging


class BaseAgent:
    """
    A simple base class for this project's agents. 
    """

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name=name)
        self._log.info('Initialized')
