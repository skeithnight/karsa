from abc import ABC, abstractmethod
from typing import Optional

class CheckpointRepository(ABC):
    """Interface for tracking projection progress/offsets."""
    
    @abstractmethod
    def get_checkpoint(self, projection_name: str) -> Optional[int]:
        """Get the last processed sequence/offset for a projection."""
        pass
        
    @abstractmethod
    def save_checkpoint(self, projection_name: str, offset: int) -> None:
        """Save the processed sequence/offset for a projection."""
        pass
