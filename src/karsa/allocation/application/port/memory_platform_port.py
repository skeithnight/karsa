import abc
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AllocationArtifactPayload:
    allocation_id: str
    thesis_id: str
    state: str
    event_type: str
    details: Dict[str, Any]

class MemoryPlatformPort(abc.ABC):
    @abc.abstractmethod
    def publish_artifact(self, payload: AllocationArtifactPayload) -> None:
        pass
