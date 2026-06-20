import uuid
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    PolicySnapshot, PortfolioContext, ProposedWeight
)
from karsa.allocation.domain.events import AllocationProposalGeneratedEvent
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.allocation.application.service.weighting_strategy import WeightingStrategy


class AllocationRecommendationService:
    """Generates allocation proposals from ranked workers."""

    def __init__(
        self,
        proposal_repo: AllocationProposalRepository,
        weighting_strategy: WeightingStrategy,
        intelligence_query_service=None,
        event_publisher=None,
    ):
        self.proposal_repo = proposal_repo
        self.weighting_strategy = weighting_strategy
        self.intelligence_query_service = intelligence_query_service
        self.event_publisher = event_publisher

    def generate_proposal(
        self,
        total_capital: float,
        ranked_workers: List[Dict[str, Any]],
        policy_id: str = "default-policy",
        journal_ref: Optional[str] = None,
    ) -> AllocationProposal:
        """Generates an allocation proposal from ranked workers.

        Args:
            total_capital: Total capital to allocate.
            ranked_workers: List of worker dicts from allocation readiness API.
            policy_id: ID of the active allocation policy.
            journal_ref: Decision Journal reference (auto-generated if not provided).

        Returns:
            The created AllocationProposal.

        Raises:
            ValueError: If no allocatable workers are available.
        """
        # Filter allocatable workers
        allocatable = [
            w for w in ranked_workers
            if w.get("eligibility_status") == "ALLOCATABLE"
        ]

        if not allocatable:
            raise ValueError("No allocatable workers available for proposal generation.")

        # Compute weights using strategy
        proposed_weights = self.weighting_strategy.compute_weights(
            ranked_workers=ranked_workers,
            total_capital=total_capital,
        )

        if not proposed_weights:
            raise ValueError("Weighting strategy produced no valid weights.")

        # Generate journal_ref if not provided
        if not journal_ref:
            journal_ref = f"urn:karsa:journal:proposal:{uuid.uuid4().hex[:16]}"

        # Compute context hash
        context_data = {
            "total_capital": total_capital,
            "policy_id": policy_id,
            "worker_count": len(allocatable),
            "weights": {urn: w.proposed_weight for urn, w in proposed_weights.items()},
        }
        context_hash = hashlib.sha256(
            json.dumps(context_data, sort_keys=True).encode()
        ).hexdigest()

        # Create policy snapshot
        policy_snapshot = PolicySnapshot(
            policy_id=policy_id,
            policy_version=1,
            policy_hash=hashlib.sha256(policy_id.encode()).hexdigest(),
            active_rules=[
                "DiversificationCap: max 40% per worker",
                "ExplorationFloor: min 5% for unproven workers",
            ],
        )

        # Compute portfolio context
        total_weight = sum(w.proposed_weight for w in proposed_weights.values())
        portfolio_context = PortfolioContext(
            current_gross_exposure=0.0,
            current_net_exposure=0.0,
            current_cash_ratio=1.0,
            current_concentration=0.0,
            projected_gross_exposure=total_weight,
            projected_net_exposure=total_weight,
            projected_cash_ratio=1.0 - total_weight,
            projected_concentration=max(
                (w.proposed_weight for w in proposed_weights.values()), default=0.0
            ),
            cash_allocation_pct=1.0 - total_weight,
            concentration_impact="LOW" if len(proposed_weights) >= 3 else "MEDIUM",
            alternatives_considered=[
                "Equal weight across all allocatable workers",
                "Top-3 only allocation",
                "Inverse drawdown weighting",
            ],
        )

        # Generate rationale
        top_worker = max(proposed_weights.values(), key=lambda w: w.ranking_score)
        proposal_rationale = (
            f"Proportional allocation across {len(proposed_weights)} allocatable workers "
            f"based on ranking scores from allocation readiness analysis. "
            f"Top performer: {top_worker.worker_urn} (score: {top_worker.ranking_score:.4f}). "
            f"Total capital: {total_capital:.2f}. "
            f"Cash reserve: {(1.0 - total_weight) * 100:.1f}%."
        )

        # Create proposal
        proposal_id = f"urn:karsa:proposal:{uuid.uuid4().hex[:16]}"
        proposal = AllocationProposal(
            proposal_id=proposal_id,
            policy_id=policy_id,
            policy_snapshot=policy_snapshot,
            journal_ref=journal_ref,
            proposed_weights=proposed_weights,
            total_capital=total_capital,
            proposal_rationale=proposal_rationale,
            portfolio_context=portfolio_context,
            context_hash=context_hash,
            generated_at=datetime.utcnow(),
        )

        # Save to write-once ledger
        self.proposal_repo.save_proposal(proposal)

        # Publish event
        if self.event_publisher:
            event = AllocationProposalGeneratedEvent(
                event_id=str(uuid.uuid4()),
                proposal_id=proposal_id,
                policy_id=policy_id,
                journal_ref=journal_ref,
                proposed_weights={
                    urn: {
                        "worker_urn": w.worker_urn,
                        "proposed_weight": w.proposed_weight,
                        "ranking_score": w.ranking_score,
                        "eligibility_status": w.eligibility_status,
                        "rationale": w.rationale,
                    }
                    for urn, w in proposed_weights.items()
                },
                total_capital=total_capital,
                proposal_rationale=proposal_rationale,
                context_hash=context_hash,
                generated_at=proposal.generated_at,
            )
            self.event_publisher.publish(event)

        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[AllocationProposal]:
        return self.proposal_repo.get_proposal_by_id(proposal_id)

    def list_proposals(self, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        return self.proposal_repo.list_proposals(limit=limit, offset=offset)
