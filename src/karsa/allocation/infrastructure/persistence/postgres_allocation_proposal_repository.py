import json
from typing import Optional, List
from datetime import datetime
import psycopg

from karsa.allocation.domain.model.allocation_proposal import AllocationProposal
from karsa.allocation.domain.model.value_objects import (
    ProposedWeight, PolicySnapshot, PortfolioContext, RiskBudget
)
from karsa.allocation.domain.repository.allocation_proposal_repository import AllocationProposalRepository
from karsa.allocation.infrastructure.persistence.mappers import (
    serialize_policy_snapshot, deserialize_policy_snapshot,
    serialize_portfolio_context, deserialize_portfolio_context,
    serialize_proposed_weights, deserialize_proposed_weights,
)
from karsa.cio.exceptions import ImmutabilityViolationException


class PostgresAllocationProposalRepository(AllocationProposalRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_proposal(self, proposal: AllocationProposal) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO allocation_proposals (
                        proposal_id, policy_id, policy_snapshot, journal_ref,
                        proposed_weights, total_capital, proposal_rationale,
                        portfolio_context, context_hash, generated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        proposal.proposal_id,
                        proposal.policy_id,
                        json.dumps(serialize_policy_snapshot(proposal.policy_snapshot)),
                        proposal.journal_ref,
                        json.dumps(serialize_proposed_weights(proposal.proposed_weights)),
                        proposal.total_capital,
                        proposal.proposal_rationale,
                        json.dumps(serialize_portfolio_context(proposal.portfolio_context)),
                        proposal.context_hash,
                        proposal.generated_at,
                    )
                )
        except psycopg.errors.RaiseException as e:
            raise ImmutabilityViolationException(str(e)) from e

    def get_proposal_by_id(self, proposal_id: str) -> Optional[AllocationProposal]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT proposal_id, policy_id, policy_snapshot, journal_ref,
                       proposed_weights, total_capital, proposal_rationale,
                       portfolio_context, context_hash, generated_at
                FROM allocation_proposals
                WHERE proposal_id = %s
                """,
                (proposal_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def list_proposals(self, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT proposal_id, policy_id, policy_snapshot, journal_ref,
                       proposed_weights, total_capital, proposal_rationale,
                       portfolio_context, context_hash, generated_at
                FROM allocation_proposals
                ORDER BY generated_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(row) for row in rows]

    def list_proposals_by_policy(self, policy_id: str, limit: int = 50, offset: int = 0) -> List[AllocationProposal]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT proposal_id, policy_id, policy_snapshot, journal_ref,
                       proposed_weights, total_capital, proposal_rationale,
                       portfolio_context, context_hash, generated_at
                FROM allocation_proposals
                WHERE policy_id = %s
                ORDER BY generated_at DESC
                LIMIT %s OFFSET %s
                """,
                (policy_id, limit, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(row) for row in rows]

    def exists(self, proposal_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM allocation_proposals WHERE proposal_id = %s",
                (proposal_id,)
            )
            return cur.fetchone() is not None

    def _row_to_aggregate(self, row) -> AllocationProposal:
        policy_data = row[2] if isinstance(row[2], dict) else json.loads(row[2])
        weights_data = row[4] if isinstance(row[4], dict) else json.loads(row[4])
        ctx_data = row[7] if isinstance(row[7], dict) else json.loads(row[7])

        policy_snapshot = deserialize_policy_snapshot(policy_data)
        proposed_weights = deserialize_proposed_weights(weights_data)
        portfolio_context = deserialize_portfolio_context(ctx_data)

        return AllocationProposal(
            proposal_id=row[0],
            policy_id=row[1],
            policy_snapshot=policy_snapshot,
            journal_ref=row[3],
            proposed_weights=proposed_weights,
            total_capital=float(row[5]),
            proposal_rationale=row[6],
            portfolio_context=portfolio_context,
            context_hash=row[8],
            generated_at=row[9],
        )
