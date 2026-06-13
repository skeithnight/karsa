from typing import List, Any
from karsa.memory.domain.model.events import EventBus

class MockEventBus(EventBus):
    def __init__(self):
        self.published_events: List[Any] = []
        
    def publish(self, event: Any) -> None:
        self.published_events.append(event)
