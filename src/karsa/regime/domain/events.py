from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    version: str = "v1"

    def to_dict(self) -> dict:
        d = asdict(self)
        d['occurred_at'] = self.occurred_at.isoformat()
        return d

@dataclass(frozen=True)
class RegimeSnapshotCreatedEvent(DomainEvent):
    snapshot_urn: str
    segment_urn: str
    horizon_urn: str
    snapshot_date: str
    regime_manifest_hash: str

@dataclass(frozen=True)
class RegimeTransitionRecordedEvent(DomainEvent):
    transition_urn: str
    from_regime_market: str
    to_regime_market: str
    supersedes_transition_urn: str | None
    transition_manifest_hash: str

@dataclass(frozen=True)
class RegimeSnapshotSupersededEvent(DomainEvent):
    snapshot_urn: str
    superseded_by_snapshot_urn: str

@dataclass(frozen=True)
class RegimeSnapshotInvalidatedEvent(DomainEvent):
    snapshot_urn: str
    invalidating_version: int
