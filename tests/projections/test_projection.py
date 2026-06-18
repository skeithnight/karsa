import pytest
from karsa.projections.base_projection import BaseProjection
from karsa.projections.checkpoint_repository import CheckpointRepository
from karsa.projections.projection_runner import ProjectionRunner
from typing import Optional, Dict, Any

class DummyProjection(BaseProjection):
    def __init__(self):
        self.processed = []
        
    @property
    def projection_name(self) -> str:
        super().projection_name
        return "dummy_projection"
        
    def handle_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        super().handle_event(event_name, payload)
        self.processed.append((event_name, payload))

class InMemoryCheckpointRepo(CheckpointRepository):
    def __init__(self):
        self.checkpoints = {}
        
    def get_checkpoint(self, projection_name: str) -> Optional[int]:
        super().get_checkpoint(projection_name)
        return self.checkpoints.get(projection_name)
        
    def save_checkpoint(self, projection_name: str, offset: int) -> None:
        super().save_checkpoint(projection_name, offset)
        self.checkpoints[projection_name] = offset

def test_projection_runner():
    proj = DummyProjection()
    repo = InMemoryCheckpointRepo()
    
    def fetcher(offset, limit):
        if offset == 0:
            return [{"sequence_id": 1, "event_name": "TestEvent", "payload": {}}]
        return []
        
    runner = ProjectionRunner(proj, repo, fetcher)
    
    # Run first batch
    processed = runner.run_batch(10)
    assert processed == 1
    assert repo.get_checkpoint("dummy_projection") == 1
    assert len(proj.processed) == 1
    
    # Run second batch (no new events)
    processed = runner.run_batch(10)
    assert processed == 0
    assert repo.get_checkpoint("dummy_projection") == 1
