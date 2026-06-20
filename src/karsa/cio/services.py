from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from cryptography.hazmat.primitives.asymmetric import ed25519
from karsa.cio.models import CIODecisionAggregate
from karsa.cio.projections import PortfolioStateProjection
from karsa.cio.value_objects import CommitteeVote, OverrideReason, SignaturePayload
from karsa.cio.repositories import CIODecisionRepository
from karsa.cio.ports import DecisionJournalPort, GovernanceExceptionPort, EventPublisherPort
from karsa.cio.exceptions import (
    QuorumNotMetException, DecisionNotFoundException,
    DuplicateJournalRefException, InvalidDecisionSignatureException
)
from karsa.cio.events import (
    PortfolioDecisionMadeEvent,
    AllocationProposalApprovedEvent,
    AllocationProposalRejectedEvent,
    AllocationProposalModifiedEvent,
)
from karsa.execution.domain.security import sign_payload


class CIODecisionService:
    def __init__(
        self,
        decision_repo: CIODecisionRepository,
        journal_port: DecisionJournalPort,
        governance_port: GovernanceExceptionPort,
        event_publisher: EventPublisherPort,
        private_key: ed25519.Ed25519PrivateKey,
        key_id: str = "cio-key-1",
        proposal_repo=None,
        projection_repo=None,
    ):
        self.decision_repo = decision_repo
        self.journal_port = journal_port
        self.governance_port = governance_port
        self.event_publisher = event_publisher
        self.private_key = private_key
        self.key_id = key_id
        self.proposal_repo = proposal_repo
        self.projection_repo = projection_repo

    def create_decision(
        self,
        decision_id: str,
        calculation_id: Optional[str],
        governance_exception_id: Optional[str],
        decision_journal_ref: str,
        portfolio_snapshot_hash: str,
        action_type: str,
        target_node_type: str,
        target_node_id: str,
        allocated_weights: Dict[str, float],
        votes: List[CommitteeVote],
        override_reason: Optional[OverrideReason] = None
    ) -> CIODecisionAggregate:
        # 1. Validate Decision Journal existence
        if not self.journal_port.verify_journal_exists(decision_journal_ref):
            raise ValueError(f"Decision Journal reference {decision_journal_ref} does not exist or is not sealed.")

        # 2. Check 1:1 cardinality locally before inserting
        existing = self.decision_repo.get_decision_by_journal_ref(decision_journal_ref)
        if existing:
            raise DuplicateJournalRefException(
                f"Decision Journal reference {decision_journal_ref} already authorizes a CIO decision."
            )

        # 3. Quorum Validation
        if action_type != "OVERRIDE":
            if not votes:
                raise QuorumNotMetException("Committee votes cannot be empty for standard allocation decisions.")
            approvals = sum(1 for v in votes if v.vote_type == "APPROVE")
            rejections = sum(1 for v in votes if v.vote_type == "REJECT")
            if approvals <= rejections:
                raise QuorumNotMetException(
                    f"Quorum check failed: approvals ({approvals}) must exceed rejections ({rejections})."
                )

        # 4. Governance Exception Token verification
        if governance_exception_id:
            payload_data = {"target_node_id": target_node_id, "allocated_weights": allocated_weights}
            is_valid_exception = self.governance_port.verify_exception_token(
                exception_id=governance_exception_id,
                signature="dummy_signature",
                payload=payload_data
            )
            if not is_valid_exception:
                raise InvalidDecisionSignatureException("Governance exception token signature verification failed.")

        # 5. Cryptographic signature generation
        sig_payload = SignaturePayload(
            decision_id=decision_id,
            target_node_id=target_node_id,
            allocated_weights=allocated_weights,
            portfolio_snapshot_hash=portfolio_snapshot_hash,
            governance_exception_id=governance_exception_id
        )
        serialized_payload = sig_payload.serialize()
        signature = sign_payload(self.private_key, serialized_payload)

        # 6. Instantiate Aggregate and Save to Ledger
        decision = CIODecisionAggregate(
            decision_id=decision_id,
            calculation_id=calculation_id,
            governance_exception_id=governance_exception_id,
            decision_journal_ref=decision_journal_ref,
            portfolio_snapshot_hash=portfolio_snapshot_hash,
            action_type=action_type,
            target_node_type=target_node_type,
            target_node_id=target_node_id,
            decision_payload={"allocated_weights": allocated_weights},
            cryptographic_signature=signature,
            created_at=datetime.utcnow(),
            votes=votes,
            override_reason=override_reason
        )
        self.decision_repo.save_decision(decision)

        # 7. Emit Domain Event
        event = PortfolioDecisionMadeEvent(
            event_id=str(uuid.uuid4()),
            event_type="PortfolioDecisionMadeEvent",
            correlation_id=decision_id,
            causation_id=calculation_id or decision_id,
            decision_id=decision_id,
            portfolio_id=target_node_id,
            actor={
                "actor_id": "cio-committee" if action_type != "OVERRIDE" else "cio-override-user",
                "actor_type": "AGENT" if action_type != "OVERRIDE" else "HUMAN"
            },
            action_type=action_type,
            payload={
                "allocated_weights": allocated_weights,
                "votes": [{"voter_id": v.voter_id, "vote_type": v.vote_type, "timestamp": v.timestamp.isoformat()} for v in votes],
                "override_reason": {"justification": override_reason.justification, "referenced_incident_urn": override_reason.referenced_incident_urn} if override_reason else None
            },
            rationale={
                "summary": override_reason.justification if override_reason else "Committee consensus allocation",
                "references": [decision_journal_ref]
            },
            cryptographic_signature={
                "key_id": self.key_id,
                "algorithm": "Ed25519",
                "signature_hex": signature
            },
            timestamp=decision.created_at
        )
        self.event_publisher.publish(event)

        return decision

    def approve_proposal(
        self,
        proposal_id: str,
        decision_id: str,
        expected_outcome,
        risk_assessment,
        review_horizon,
        votes: List[CommitteeVote],
        actor_id: str = "cio-committee",
    ) -> CIODecisionAggregate:
        """Approves an allocation proposal and creates a CIO decision.

        Args:
            proposal_id: ID of the proposal to approve.
            decision_id: Unique ID for the new decision.
            expected_outcome: ExpectedOutcome value object.
            risk_assessment: RiskAssessment value object.
            review_horizon: ReviewHorizon value object.
            votes: Committee votes.
            actor_id: ID of the approving actor.

        Returns:
            The created CIODecisionAggregate.

        Raises:
            ValueError: If proposal not found.
            ValueError: If proposal status is not PENDING.
            ValueError: If journal does not exist.
            DuplicateJournalRefException: If journal already consumed.
            QuorumNotMetException: If quorum not met.
        """
        # 1. Validate proposal exists
        if not self.proposal_repo:
            raise ValueError("Proposal repository not configured.")
        proposal = self.proposal_repo.get_proposal_by_id(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        # 2. Validate projection status is PENDING
        if self.projection_repo:
            status = self.projection_repo.get_status(proposal_id)
            if status and status.status != "PENDING":
                raise ValueError(f"Proposal {proposal_id} is not PENDING (current status: {status.status}).")

        # 3. Validate journal exists
        if not self.journal_port.verify_journal_exists(proposal.journal_ref):
            raise ValueError(f"Decision Journal {proposal.journal_ref} does not exist.")

        # 4. Validate journal not already consumed
        if self.decision_repo.exists_by_journal_ref(proposal.journal_ref):
            raise DuplicateJournalRefException(
                f"Decision Journal {proposal.journal_ref} already authorizes a CIO decision."
            )

        # 5. Quorum validation
        if not votes:
            raise QuorumNotMetException("Committee votes cannot be empty.")
        approvals = sum(1 for v in votes if v.vote_type == "APPROVE")
        rejections = sum(1 for v in votes if v.vote_type == "REJECT")
        if approvals <= rejections:
            raise QuorumNotMetException(
                f"Quorum check failed: approvals ({approvals}) must exceed rejections ({rejections})."
            )

        # 6. Extract weights from proposal
        allocated_weights = {urn: w.proposed_weight for urn, w in proposal.proposed_weights.items()}

        # 7. Generate signature
        sig_payload = SignaturePayload(
            decision_id=decision_id,
            target_node_id="portfolio-main",
            allocated_weights=allocated_weights,
            portfolio_snapshot_hash=proposal.context_hash,
        )
        signature = sign_payload(self.private_key, sig_payload.serialize())

        # 8. Create decision
        decision = CIODecisionAggregate(
            decision_id=decision_id,
            calculation_id=None,
            governance_exception_id=None,
            decision_journal_ref=proposal.journal_ref,
            portfolio_snapshot_hash=proposal.context_hash,
            action_type="APPROVE_ALLOCATION",
            target_node_type="WORKER",
            target_node_id="portfolio-main",
            decision_payload={"allocated_weights": allocated_weights},
            cryptographic_signature=signature,
            created_at=datetime.utcnow(),
            votes=votes,
            proposal_id=proposal_id,
            expected_outcome=expected_outcome,
            risk_assessment=risk_assessment,
            review_horizon=review_horizon,
        )
        self.decision_repo.save_decision(decision)

        # 9. Publish events
        now = datetime.utcnow()
        event_seq = int(now.timestamp() * 1000)

        approved_event = AllocationProposalApprovedEvent(
            event_id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            decision_id=decision_id,
            approved_by=actor_id,
            approved_at=now,
            event_sequence=event_seq,
        )
        self.event_publisher.publish(approved_event)

        portfolio_event = PortfolioDecisionMadeEvent(
            event_id=str(uuid.uuid4()),
            event_type="PortfolioDecisionMadeEvent",
            correlation_id=decision_id,
            causation_id=proposal_id,
            decision_id=decision_id,
            portfolio_id="portfolio-main",
            actor={"actor_id": actor_id, "actor_type": "HUMAN"},
            action_type="APPROVE_ALLOCATION",
            payload={
                "allocated_weights": allocated_weights,
                "votes": [{"voter_id": v.voter_id, "vote_type": v.vote_type, "timestamp": v.timestamp.isoformat()} for v in votes],
            },
            rationale={
                "summary": f"Approved allocation proposal {proposal_id}",
                "references": [proposal.journal_ref],
            },
            cryptographic_signature={
                "key_id": self.key_id,
                "algorithm": "Ed25519",
                "signature_hex": signature,
            },
            timestamp=now,
        )
        self.event_publisher.publish(portfolio_event)

        return decision

    def reject_proposal(
        self,
        proposal_id: str,
        decision_id: str,
        rejection_reason: str,
        votes: List[CommitteeVote],
        actor_id: str = "cio-committee",
    ) -> CIODecisionAggregate:
        """Rejects an allocation proposal."""
        # 1. Validate proposal
        if not self.proposal_repo:
            raise ValueError("Proposal repository not configured.")
        proposal = self.proposal_repo.get_proposal_by_id(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        # 2. Validate status
        if self.projection_repo:
            status = self.projection_repo.get_status(proposal_id)
            if status and status.status != "PENDING":
                raise ValueError(f"Proposal {proposal_id} is not PENDING.")

        # 3. Validate journal
        if not self.journal_port.verify_journal_exists(proposal.journal_ref):
            raise ValueError(f"Decision Journal {proposal.journal_ref} does not exist.")

        if self.decision_repo.exists_by_journal_ref(proposal.journal_ref):
            raise DuplicateJournalRefException(
                f"Decision Journal {proposal.journal_ref} already authorizes a CIO decision."
            )

        # 4. Quorum
        if not votes:
            raise QuorumNotMetException("Committee votes cannot be empty.")
        approvals = sum(1 for v in votes if v.vote_type == "APPROVE")
        rejections = sum(1 for v in votes if v.vote_type == "REJECT")
        # For rejection, rejections must exceed approvals
        if rejections <= approvals:
            raise QuorumNotMetException(
                f"Rejection quorum check failed: rejections ({rejections}) must exceed approvals ({approvals})."
            )

        # 5. Create decision
        allocated_weights = {urn: w.proposed_weight for urn, w in proposal.proposed_weights.items()}
        sig_payload = SignaturePayload(
            decision_id=decision_id,
            target_node_id="portfolio-main",
            allocated_weights=allocated_weights,
            portfolio_snapshot_hash=proposal.context_hash,
        )
        signature = sign_payload(self.private_key, sig_payload.serialize())

        override_reason = OverrideReason(justification=rejection_reason)
        decision = CIODecisionAggregate(
            decision_id=decision_id,
            calculation_id=None,
            governance_exception_id=None,
            decision_journal_ref=proposal.journal_ref,
            portfolio_snapshot_hash=proposal.context_hash,
            action_type="REJECT_ALLOCATION",
            target_node_type="WORKER",
            target_node_id="portfolio-main",
            decision_payload={"allocated_weights": allocated_weights},
            cryptographic_signature=signature,
            created_at=datetime.utcnow(),
            votes=votes,
            override_reason=override_reason,
            proposal_id=proposal_id,
        )
        self.decision_repo.save_decision(decision)

        # 6. Publish events
        now = datetime.utcnow()
        event_seq = int(now.timestamp() * 1000)

        rejected_event = AllocationProposalRejectedEvent(
            event_id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            decision_id=decision_id,
            rejected_by=actor_id,
            rejection_reason=rejection_reason,
            rejected_at=now,
            event_sequence=event_seq,
        )
        self.event_publisher.publish(rejected_event)

        portfolio_event = PortfolioDecisionMadeEvent(
            event_id=str(uuid.uuid4()),
            event_type="PortfolioDecisionMadeEvent",
            correlation_id=decision_id,
            causation_id=proposal_id,
            decision_id=decision_id,
            portfolio_id="portfolio-main",
            actor={"actor_id": actor_id, "actor_type": "HUMAN"},
            action_type="REJECT_ALLOCATION",
            payload={
                "allocated_weights": allocated_weights,
                "votes": [{"voter_id": v.voter_id, "vote_type": v.vote_type, "timestamp": v.timestamp.isoformat()} for v in votes],
                "override_reason": {"justification": rejection_reason, "referenced_incident_urn": None},
            },
            rationale={
                "summary": rejection_reason,
                "references": [proposal.journal_ref],
            },
            cryptographic_signature={
                "key_id": self.key_id,
                "algorithm": "Ed25519",
                "signature_hex": signature,
            },
            timestamp=now,
        )
        self.event_publisher.publish(portfolio_event)

        return decision

    def modify_proposal(
        self,
        proposal_id: str,
        decision_id: str,
        modified_weights: Dict[str, float],
        modification_reason: str,
        expected_outcome,
        risk_assessment,
        review_horizon,
        votes: List[CommitteeVote],
        actor_id: str = "cio-committee",
    ) -> CIODecisionAggregate:
        """Modifies an allocation proposal with new weights."""
        # 1. Validate proposal
        if not self.proposal_repo:
            raise ValueError("Proposal repository not configured.")
        proposal = self.proposal_repo.get_proposal_by_id(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        # 2. Validate status
        if self.projection_repo:
            status = self.projection_repo.get_status(proposal_id)
            if status and status.status != "PENDING":
                raise ValueError(f"Proposal {proposal_id} is not PENDING.")

        # 3. Validate weights
        if not modified_weights:
            raise ValueError("modified_weights cannot be empty.")
        total_weight = sum(modified_weights.values())
        if total_weight > 1.0 + 1e-9:
            raise ValueError(f"Modified weights sum to {total_weight}, which exceeds 1.0.")
        for urn, weight in modified_weights.items():
            if weight < 0:
                raise ValueError(f"Weight for {urn} cannot be negative.")

        # 4. Validate journal
        if not self.journal_port.verify_journal_exists(proposal.journal_ref):
            raise ValueError(f"Decision Journal {proposal.journal_ref} does not exist.")

        if self.decision_repo.exists_by_journal_ref(proposal.journal_ref):
            raise DuplicateJournalRefException(
                f"Decision Journal {proposal.journal_ref} already authorizes a CIO decision."
            )

        # 5. Quorum
        if not votes:
            raise QuorumNotMetException("Committee votes cannot be empty.")
        approvals = sum(1 for v in votes if v.vote_type == "APPROVE")
        rejections = sum(1 for v in votes if v.vote_type == "REJECT")
        if approvals <= rejections:
            raise QuorumNotMetException(
                f"Quorum check failed: approvals ({approvals}) must exceed rejections ({rejections})."
            )

        # 6. Create decision
        sig_payload = SignaturePayload(
            decision_id=decision_id,
            target_node_id="portfolio-main",
            allocated_weights=modified_weights,
            portfolio_snapshot_hash=proposal.context_hash,
        )
        signature = sign_payload(self.private_key, sig_payload.serialize())

        override_reason = OverrideReason(justification=modification_reason)
        decision = CIODecisionAggregate(
            decision_id=decision_id,
            calculation_id=None,
            governance_exception_id=None,
            decision_journal_ref=proposal.journal_ref,
            portfolio_snapshot_hash=proposal.context_hash,
            action_type="OVERRIDE",
            target_node_type="WORKER",
            target_node_id="portfolio-main",
            decision_payload={"allocated_weights": modified_weights},
            cryptographic_signature=signature,
            created_at=datetime.utcnow(),
            votes=votes,
            override_reason=override_reason,
            proposal_id=proposal_id,
            expected_outcome=expected_outcome,
            risk_assessment=risk_assessment,
            review_horizon=review_horizon,
        )
        self.decision_repo.save_decision(decision)

        # 7. Publish events
        now = datetime.utcnow()
        event_seq = int(now.timestamp() * 1000)

        modified_event = AllocationProposalModifiedEvent(
            event_id=str(uuid.uuid4()),
            original_proposal_id=proposal_id,
            decision_id=decision_id,
            modified_weights=modified_weights,
            modification_reason=modification_reason,
            modified_by=actor_id,
            modified_at=now,
            event_sequence=event_seq,
        )
        self.event_publisher.publish(modified_event)

        portfolio_event = PortfolioDecisionMadeEvent(
            event_id=str(uuid.uuid4()),
            event_type="PortfolioDecisionMadeEvent",
            correlation_id=decision_id,
            causation_id=proposal_id,
            decision_id=decision_id,
            portfolio_id="portfolio-main",
            actor={"actor_id": actor_id, "actor_type": "HUMAN"},
            action_type="OVERRIDE",
            payload={
                "allocated_weights": modified_weights,
                "votes": [{"voter_id": v.voter_id, "vote_type": v.vote_type, "timestamp": v.timestamp.isoformat()} for v in votes],
                "override_reason": {"justification": modification_reason, "referenced_incident_urn": None},
            },
            rationale={
                "summary": modification_reason,
                "references": [proposal.journal_ref],
            },
            cryptographic_signature={
                "key_id": self.key_id,
                "algorithm": "Ed25519",
                "signature_hex": signature,
            },
            timestamp=now,
        )
        self.event_publisher.publish(portfolio_event)

        return decision

    def get_decision(self, decision_id: str) -> CIODecisionAggregate:
        decision = self.decision_repo.get_decision_by_id(decision_id)
        if not decision:
            raise DecisionNotFoundException(f"CIO decision {decision_id} not found.")
        return decision

    def list_decisions(self, limit: int = 50, offset: int = 0) -> List[CIODecisionAggregate]:
        return self.decision_repo.list_decisions(limit=limit, offset=offset)


class PortfolioOrchestrationService:
    def __init__(self, decision_repo: CIODecisionRepository):
        self.decision_repo = decision_repo

    def project_state(self, state_id: str, decision_id: str, portfolio_tree: Dict[str, Any]) -> PortfolioStateProjection:
        state = PortfolioStateProjection(
            state_id=state_id,
            decision_id=decision_id,
            portfolio_tree=portfolio_tree,
            created_at=datetime.utcnow()
        )
        self.decision_repo.save_portfolio_state(state)
        return state

    def get_latest_state(self) -> Optional[PortfolioStateProjection]:
        return self.decision_repo.get_latest_portfolio_state()
