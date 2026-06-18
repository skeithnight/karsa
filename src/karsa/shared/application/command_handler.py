from typing import TypeVar, Generic
from abc import ABC, abstractmethod

C = TypeVar('C')

class CommandHandler(Generic[C], ABC):
    """Base class for command handlers."""
    
    @abstractmethod
    def handle(self, command: C) -> None:
        pass
