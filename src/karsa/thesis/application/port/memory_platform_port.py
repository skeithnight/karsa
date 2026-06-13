import abc
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ArtifactPayload:
    thesis_id: str
    state: str
    author: str
    event_type: str
    details: Dict[str, Any]

class MemoryPlatformPort(abc.ABC):
    @abc.abstractmethod
    def publish_artifact(self, payload: ArtifactPayload) -> None:
        pass
