from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, payload: Dict[str, Any], state_manager) -> dict:
        """
        Executes the trading logic based on the webhook payload.
        Must be implemented by all child classes.
        """
        pass