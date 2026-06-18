import time
from typing import List, Dict, Any, Callable
from .base_projection import BaseProjection
from .checkpoint_repository import CheckpointRepository

class ProjectionRunner:
    """Runner that polls an event source and updates a projection."""
    def __init__(
        self,
        projection: BaseProjection,
        checkpoint_repo: CheckpointRepository,
        event_fetcher: Callable[[int, int], List[Dict[str, Any]]] # fetcher(offset, limit) -> events
    ):
        self.projection = projection
        self.checkpoint_repo = checkpoint_repo
        self.event_fetcher = event_fetcher

    def run_batch(self, limit: int = 100) -> int:
        """Run a single batch of projection updates."""
        offset = self.checkpoint_repo.get_checkpoint(self.projection.projection_name) or 0
        events = self.event_fetcher(offset, limit)
        
        if not events:
            return 0
            
        for event in events:
            self.projection.handle_event(event["event_name"], event["payload"])
            offset = event["sequence_id"] # assuming sequence_id is the monotonic offset
            
        self.checkpoint_repo.save_checkpoint(self.projection.projection_name, offset)
        return len(events)
