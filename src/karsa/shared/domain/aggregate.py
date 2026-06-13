from dataclasses import dataclass, field
import datetime

@dataclass
class VersionedAggregate:
    """Base class for optimistic concurrency control tracking."""
    aggregate_version: int = 0
    
    def increment_version(self) -> None:
        """Increment the aggregate version. Must be called upon structural mutation."""
        self.aggregate_version += 1
