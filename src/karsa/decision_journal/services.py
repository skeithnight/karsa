from datetime import datetime
import hashlib
import json
from typing import Optional, List, Dict
from karsa.decision_journal.exceptions import (
    HindsightValidationException, LineageIntegrityException, VerificationFailedException, ActiveLeafNotFoundException
)
from karsa.decision_journal.models import DecisionJournalAggregate, DecisionRevisionAggregate, DecisionEvidenceAggregate
from karsa.decision_journal.value_objects import DecisionContextSnapshot, DecisionEvidence
from karsa.decision_journal.events import (
    DecisionJournalCreatedEvent, DecisionRevisionCreatedEvent, DecisionEvidenceAttachedEvent
)
from karsa.decision_journal.projections import ActiveLeafProjection, ReasoningLineageProjection, ReplayProjection
from karsa.decision_journal.ports import ObjectStorePort, EventPublisherPort
from karsa.decision_journal.repositories import DecisionJournalRepository, ActiveLeafProjectionRepository
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

class DecisionJournalService:
    def __init__(
        self,
        journal_repo: DecisionJournalRepository,
        leaf_repo: ActiveLeafProjectionRepository,
        object_store: ObjectStorePort,
        event_publisher: EventPublisherPort
    ):
        self.journal_repo = journal_repo
        self.leaf_repo = leaf_repo
        self.object_store = object_store
        self.event_publisher = event_publisher
        self._executed_decisions = set() # Mock set to simulate execution start in tests

    def set_execution_started(self, decision_id: str) -> None:
        self._executed_decisions.add(decision_id)

    def create_journal(
        self,
        decision_id: str,
        proposing_agent_id: str,
        signature: str,
        thesis_urn: str,
        context_snapshot: DecisionContextSnapshot,
        probability: float = 1.0
    ) -> DecisionJournalAggregate:
        # Validate confidence bounds
        if not (0.0 <= probability <= 1.0):
            raise ValueError(f"Confidence probability {probability} must be between 0.0 and 1.0.")

        # Offload context snapshot to object store
        uri = self.object_store.save_context_snapshot(decision_id, context_snapshot)
        context_hash = hashlib.sha256(str(context_snapshot).encode('utf-8')).hexdigest()

        journal = DecisionJournalAggregate(
            decision_id=decision_id,
            proposing_agent_id=proposing_agent_id,
            signature=signature,
            thesis_urn=thesis_urn,
            context_snapshot=context_snapshot,
            created_at=datetime.utcnow(),
            context_hash=context_hash,
            context_uri=uri
        )

        self.journal_repo.save_journal(journal)

        # Initialize active leaf projection
        leaf = ActiveLeafProjection(
            root_decision_id=decision_id,
            active_leaf_decision_id=decision_id,
            version=1,
            updated_at=datetime.utcnow()
        )
        self.leaf_repo.save_active_leaf(leaf)

        # Emit event
        event = DecisionJournalCreatedEvent(
            event_id=f"evt-dj-created-{uuid_helper()}",
            decision_id=decision_id,
            proposing_agent_id=proposing_agent_id,
            thesis_urn=thesis_urn,
            context_hash=context_hash,
            context_uri=uri,
            timestamp=journal.created_at
        )
        self.event_publisher.publish(event)

        return journal

    def create_revision(
        self,
        revision_id: str,
        parent_decision_id: str,
        proposing_agent_id: str,
        signature: str,
        correction_reason: str,
        context_snapshot: DecisionContextSnapshot
    ) -> DecisionRevisionAggregate:
        # Check lineage parent existence
        parent = self.journal_repo.get_journal_by_id(parent_decision_id)
        if not parent:
            # Check revisions as well
            parent_rev = self.journal_repo.get_revision_by_id(parent_decision_id)
            if not parent_rev:
                raise LineageIntegrityException(f"Parent decision ID {parent_decision_id} does not exist.")
            root_decision_id = parent_rev.root_decision_id
        else:
            root_decision_id = parent.decision_id

        # Verify execution has not started (hindsight prevention)
        if root_decision_id in self._executed_decisions or parent_decision_id in self._executed_decisions:
            raise HindsightValidationException("Cannot append correction: trade execution has already started.")

        # Offload context snapshot to object store
        uri = self.object_store.save_context_snapshot(revision_id, context_snapshot)
        context_hash = hashlib.sha256(str(context_snapshot).encode('utf-8')).hexdigest()

        revision = DecisionRevisionAggregate(
            revision_id=revision_id,
            parent_decision_id=parent_decision_id,
            root_decision_id=root_decision_id,
            proposing_agent_id=proposing_agent_id,
            signature=signature,
            correction_reason=correction_reason,
            context_snapshot=context_snapshot,
            created_at=datetime.utcnow(),
            context_hash=context_hash,
            context_uri=uri
        )

        self.journal_repo.save_revision(revision)

        # Update active leaf projection under OCC
        active_leaf = self.leaf_repo.get_active_leaf(root_decision_id)
        if not active_leaf:
            raise ActiveLeafNotFoundException(f"Active leaf not found for root decision {root_decision_id}")

        new_leaf = ActiveLeafProjection(
            root_decision_id=root_decision_id,
            active_leaf_decision_id=revision_id,
            version=active_leaf.version + 1,
            updated_at=datetime.utcnow()
        )
        self.leaf_repo.save_active_leaf(new_leaf)

        # Emit event
        event = DecisionRevisionCreatedEvent(
            event_id=f"evt-dr-created-{uuid_helper()}",
            revision_id=revision_id,
            parent_decision_id=parent_decision_id,
            root_decision_id=root_decision_id,
            proposing_agent_id=proposing_agent_id,
            context_hash=context_hash,
            context_uri=uri,
            timestamp=revision.created_at
        )
        self.event_publisher.publish(event)

        return revision

    def attach_evidence(
        self,
        evidence_id: str,
        decision_id: str,
        attached_by_agent_id: str,
        signature: str,
        evidence: DecisionEvidence
    ) -> DecisionEvidenceAggregate:
        # Verify journal exists
        journal = self.journal_repo.get_journal_by_id(decision_id)
        if not journal:
            raise LineageIntegrityException(f"Decision ID {decision_id} does not exist.")

        evidence_agg = DecisionEvidenceAggregate(
            evidence_id=evidence_id,
            decision_id=decision_id,
            attached_by_agent_id=attached_by_agent_id,
            signature=signature,
            evidence=evidence,
            created_at=datetime.utcnow()
        )

        self.journal_repo.save_evidence(evidence_agg)

        # Emit event
        event = DecisionEvidenceAttachedEvent(
            event_id=f"evt-de-attached-{uuid_helper()}",
            evidence_id=evidence_id,
            decision_id=decision_id,
            attached_by_agent_id=attached_by_agent_id,
            evidence_hash=evidence.artifact_ref.artifact_hash,
            timestamp=evidence_agg.created_at
        )
        self.event_publisher.publish(event)

        return evidence_agg

class JournalLineageResolver:
    def __init__(self, leaf_repo: ActiveLeafProjectionRepository, journal_repo: DecisionJournalRepository):
        self.leaf_repo = leaf_repo
        self.journal_repo = journal_repo

    def resolve_active_leaf(self, root_decision_id: str) -> str:
        leaf = self.leaf_repo.get_active_leaf(root_decision_id)
        if not leaf:
            raise ActiveLeafNotFoundException(f"Active leaf not found for root decision {root_decision_id}")
        return leaf.active_leaf_decision_id

    def resolve_lineage(self, root_decision_id: str) -> ReasoningLineageProjection:
        root_journal = self.journal_repo.get_journal_by_id(root_decision_id)
        if not root_journal:
            raise LineageIntegrityException(f"Root decision ID {root_decision_id} not found.")

        revisions = self.journal_repo.get_all_revisions_by_root_id(root_decision_id)
        
        nodes = [root_decision_id]
        parent_map = {}
        
        for rev in revisions:
            nodes.append(rev.revision_id)
            parent_map[rev.revision_id] = rev.parent_decision_id

        return ReasoningLineageProjection(
            root_decision_id=root_decision_id,
            nodes=nodes,
            parent_map=parent_map
        )

class ReplayService:
    def __init__(self, object_store: ObjectStorePort):
        self.object_store = object_store

    def replay_decision(self, decision_id: str, expected_hash: str, context_uri: str) -> ReplayProjection:
        snapshot = self.object_store.get_context_snapshot(context_uri)
        if not snapshot:
            raise VerificationFailedException(f"Failed to retrieve context snapshot from {context_uri}")

        valid = self.object_store.verify_hash(snapshot, expected_hash)
        if not valid:
            raise VerificationFailedException("Checksum verification failed: Context snapshot has been tampered with.")

        return ReplayProjection(
            decision_id=decision_id,
            context_snapshot=snapshot,
            verified=True
        )

def uuid_helper() -> str:
    import uuid
    return str(uuid.uuid4())[:8]
