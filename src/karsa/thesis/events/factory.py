import uuid
from datetime import datetime, timezone
from karsa.shared.events.envelope import PlatformEventEnvelope
from karsa.thesis.domain.model.thesis import Thesis
from karsa.thesis.domain.model.snapshot import ThesisSnapshotFactory
from karsa.thesis.domain.model.value_objects import ThesisReviewRecord
from karsa.thesis.events.thesis_events import (
    ThesisProposedPayload, ThesisActivatedPayload, ThesisRejectedPayload,
    ThesisConfidenceUpdatedPayload, ThesisInvalidatedPayload,
    ThesisRealizedPayload, ThesisReviewedPayload
)

class ThesisEventFactory:
    """Builds PlatformEventEnvelope for Thesis events."""
    
    @staticmethod
    def _create_envelope(thesis: Thesis, payload: any, event_type: str, causation_id: str = None) -> PlatformEventEnvelope:
        return PlatformEventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            correlation_id=thesis.identity.thesis_id,
            causation_id=causation_id or thesis.identity.thesis_id,
            aggregate_type="Thesis",
            aggregate_id=thesis.identity.thesis_id,
            aggregate_version=thesis.aggregate_version,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            schema_version="1.0",
            payload=payload
        )

    @staticmethod
    def build_proposed(thesis: Thesis, causation_id: str = None) -> PlatformEventEnvelope:
        snapshot = ThesisSnapshotFactory.build(thesis)
        return ThesisEventFactory._create_envelope(
            thesis, ThesisProposedPayload(thesis=snapshot), "ThesisProposedEvent", causation_id
        )

    @staticmethod
    def build_activated(thesis: Thesis, causation_id: str = None) -> PlatformEventEnvelope:
        snapshot = ThesisSnapshotFactory.build(thesis)
        return ThesisEventFactory._create_envelope(
            thesis, ThesisActivatedPayload(thesis=snapshot), "ThesisActivatedEvent", causation_id
        )

    @staticmethod
    def build_rejected(thesis: Thesis, causation_id: str = None) -> PlatformEventEnvelope:
        snapshot = ThesisSnapshotFactory.build(thesis)
        return ThesisEventFactory._create_envelope(
            thesis, ThesisRejectedPayload(thesis=snapshot), "ThesisRejectedEvent", causation_id
        )

    @staticmethod
    def build_confidence_updated(thesis: Thesis, causation_id: str = None) -> PlatformEventEnvelope:
        snapshot = ThesisSnapshotFactory.build(thesis)
        return ThesisEventFactory._create_envelope(
            thesis, ThesisConfidenceUpdatedPayload(thesis=snapshot), "ThesisConfidenceUpdatedEvent", causation_id
        )

    @staticmethod
    def build_invalidated(thesis: Thesis, causation_id: str = None) -> PlatformEventEnvelope:
        snapshot = ThesisSnapshotFactory.build(thesis)
        return ThesisEventFactory._create_envelope(
            thesis, ThesisInvalidatedPayload(thesis=snapshot), "ThesisInvalidatedEvent", causation_id
        )

    @staticmethod
    def build_realized(thesis: Thesis, causation_id: str = None) -> PlatformEventEnvelope:
        snapshot = ThesisSnapshotFactory.build(thesis)
        return ThesisEventFactory._create_envelope(
            thesis, ThesisRealizedPayload(thesis=snapshot), "ThesisRealizedEvent", causation_id
        )

    @staticmethod
    def build_reviewed(thesis_id: str, review: ThesisReviewRecord, causation_id: str = None) -> PlatformEventEnvelope:
        payload = ThesisReviewedPayload(thesis_id=thesis_id, review=review)
        return PlatformEventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type="ThesisReviewedEvent",
            correlation_id=thesis_id,
            causation_id=causation_id or thesis_id,
            aggregate_type="Thesis",
            aggregate_id=thesis_id,
            aggregate_version=0,  # Does not mutate aggregate
            occurred_at=datetime.now(timezone.utc).isoformat(),
            schema_version="1.0",
            payload=payload
        )
