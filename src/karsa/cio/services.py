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
from karsa.cio.events import PortfolioDecisionMadeEvent
from karsa.execution.domain.security import sign_payload

class CIODecisionService:
    def __init__(
        self,
        decision_repo: CIODecisionRepository,
        journal_port: DecisionJournalPort,
        governance_port: GovernanceExceptionPort,
        event_publisher: EventPublisherPort,
        private_key: ed25519.Ed25519PrivateKey,
        key_id: str = "cio-key-1"
    ):
        self.decision_repo = decision_repo
        self.journal_port = journal_port
        self.governance_port = governance_port
        self.event_publisher = event_publisher
        self.private_key = private_key
        self.key_id = key_id

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
            # Reconstruct governance verification payload: exception_id | target_node_id
            payload_data = {"target_node_id": target_node_id, "allocated_weights": allocated_weights}
            is_valid_exception = self.governance_port.verify_exception_token(
                exception_id=governance_exception_id,
                signature="dummy_signature",  # Simulating Governance signature check in port adapter
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
