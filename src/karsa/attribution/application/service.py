import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.attribution.infrastructure.repositories import AttributionRepository
from karsa.attribution.events.events import (
    DecisionLineageCreatedEvent,
    LineageNodeAddedEvent,
    AttributionFactGeneratedEvent,
    AttributionAssessmentSealedEvent
)

class AttributionLineageService:
    """Service responsible for creating and expanding lineages."""
    def __init__(
        self,
        event_journal: EventJournalRepository,
        attribution_repo: AttributionRepository
    ):
        self.event_journal = event_journal
        self.attribution_repo = attribution_repo

    def create_lineage(self, decision_id: str, forecast_id: str) -> str:
        lineage_id = str(uuid.uuid4())
        event = DecisionLineageCreatedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=lineage_id,
            causation_id=decision_id,
            lineage_id=lineage_id,
            decision_id=decision_id,
            forecast_id=forecast_id
        )
        event.stream_id = lineage_id
        version = self.event_journal.get_current_stream_version(lineage_id) + 1
        self.event_journal.append(event, stream_version=version)
        return lineage_id

    def add_lineage_node(
        self,
        lineage_id: str,
        capability_id: str,
        worker_urn: str,
        role: str
    ) -> str:
        # We can optionally query attribution_repo here for invariants
        # e.g., linege_id exists, but in a reactive design we might skip if we trust the caller.
        
        node_id = str(uuid.uuid4())
        event = LineageNodeAddedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=lineage_id,
            causation_id=lineage_id,
            lineage_id=lineage_id,
            node_id=node_id,
            capability_id=capability_id,
            worker_urn=worker_urn,
            role=role
        )
        event.stream_id = lineage_id
        version = self.event_journal.get_current_stream_version(lineage_id) + 1
        self.event_journal.append(event, stream_version=version)
        return node_id


class AttributionAssessmentService:
    """Service responsible for generating factual assessments."""
    def __init__(
        self,
        event_journal: EventJournalRepository,
        attribution_repo: AttributionRepository
    ):
        self.event_journal = event_journal
        self.attribution_repo = attribution_repo

    def generate_fact(
        self,
        lineage_id: str,
        assessment_id: str,
        dimensions: Dict[str, Any]
    ) -> str:
        fact_id = str(uuid.uuid4())
        event = AttributionFactGeneratedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=lineage_id,
            causation_id=assessment_id,
            lineage_id=lineage_id,
            fact_id=fact_id,
            assessment_id=assessment_id,
            dimensions=dimensions
        )
        event.stream_id = assessment_id
        version = self.event_journal.get_current_stream_version(assessment_id) + 1
        self.event_journal.append(event, stream_version=version)
        return fact_id

    def seal_assessment(
        self,
        assessment_id: str,
        lineage_id: str,
        fact_ids: List[str],
        provenance_urn: str
    ) -> None:
        event = AttributionAssessmentSealedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=lineage_id,
            causation_id=assessment_id,
            assessment_id=assessment_id,
            lineage_id=lineage_id,
            fact_ids_list=fact_ids,
            fact_count=len(fact_ids),
            provenance_urn=provenance_urn
        )
        # Note: the event_journal logic often propagates to event_outbox directly,
        # but the schema enforces outbox writing if needed.
        event.stream_id = assessment_id
        version = self.event_journal.get_current_stream_version(assessment_id) + 1
        self.event_journal.append(event, stream_version=version)
