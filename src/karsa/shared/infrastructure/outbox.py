from dataclasses import dataclass
from typing import Optional

@dataclass
class OutboxRecord:
    """Represents a staged event to be published asynchronously."""
    envelope_id: str
    payload: str  # JSON string of PlatformEventEnvelope
    published_status: bool = False

class Dispatcher:
    """
    Abstract Dispatcher daemon.
    In a real implementation, this runs a SELECT FOR UPDATE SKIP LOCKED
    polling loop and dispatches OutboxRecords to an Event Bus.
    """
    def dispatch_pending(self):
        """Finds unpublished OutboxRecords, publishes them, and marks them published."""
        raise NotImplementedError
