from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import psycopg
from karsa.cio.models import CIODecisionAggregate
from karsa.cio.projections import PortfolioStateProjection
from karsa.cio.value_objects import CommitteeVote, OverrideReason
from karsa.cio.exceptions import ImmutabilityViolationException, DuplicateJournalRefException

class CIODecisionRepository(ABC):
    @abstractmethod
    def save_decision(self, decision: CIODecisionAggregate) -> None:
        """Saves a CIO decision to the ledger. Raises ImmutabilityViolationException on overwrite."""
        pass

    @abstractmethod
    def get_decision_by_id(self, decision_id: str) -> Optional[CIODecisionAggregate]:
        """Retrieves a CIO decision by its unique URN."""
        pass

    @abstractmethod
    def get_decision_by_journal_ref(self, journal_ref: str) -> Optional[CIODecisionAggregate]:
        """Retrieves a CIO decision by its Decision Journal reference."""
        pass

    @abstractmethod
    def list_decisions(self, limit: int = 50, offset: int = 0) -> List[CIODecisionAggregate]:
        """Retrieves a paginated list of CIO decisions sorted by creation date."""
        pass

    @abstractmethod
    def save_portfolio_state(self, state: PortfolioStateProjection) -> None:
        """Saves a projected portfolio tree state."""
        pass

    @abstractmethod
    def get_latest_portfolio_state(self) -> Optional[PortfolioStateProjection]:
        """Retrieves the active/latest projected portfolio state."""
        pass

class InMemoryCIODecisionRepository(CIODecisionRepository):
    def __init__(self):
        self._decisions: Dict[str, CIODecisionAggregate] = {}
        self._states: List[PortfolioStateProjection] = []

    def save_decision(self, decision: CIODecisionAggregate) -> None:
        if decision.decision_id in self._decisions:
            raise ImmutabilityViolationException("Cannot overwrite an existing CIO decision record.")
        
        # Enforce 1:1 Decision Journal cardinality
        for existing in self._decisions.values():
            if existing.decision_journal_ref == decision.decision_journal_ref:
                raise DuplicateJournalRefException(
                    f"Decision Journal reference {decision.decision_journal_ref} already authorizes a CIO decision."
                )
                
        self._decisions[decision.decision_id] = decision

    def get_decision_by_id(self, decision_id: str) -> Optional[CIODecisionAggregate]:
        return self._decisions.get(decision_id)

    def get_decision_by_journal_ref(self, journal_ref: str) -> Optional[CIODecisionAggregate]:
        for d in self._decisions.values():
            if d.decision_journal_ref == journal_ref:
                return d
        return None

    def list_decisions(self, limit: int = 50, offset: int = 0) -> List[CIODecisionAggregate]:
        decisions = sorted(self._decisions.values(), key=lambda d: d.created_at, reverse=True)
        return decisions[offset:offset+limit]

    def save_portfolio_state(self, state: PortfolioStateProjection) -> None:
        # Check uniqueness to simulate trigger
        for existing in self._states:
            if existing.state_id == state.state_id:
                raise ImmutabilityViolationException("Cannot overwrite an existing portfolio state record.")
        self._states.append(state)

    def get_latest_portfolio_state(self) -> Optional[PortfolioStateProjection]:
        if not self._states:
            return None
        # Return state with latest created_at
        return max(self._states, key=lambda s: s.created_at)

class PostgresCIODecisionRepository(CIODecisionRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_decision(self, decision: CIODecisionAggregate) -> None:
        # Serialize votes and override reason into decision_payload
        votes_data = [
            {
                "voter_id": v.voter_id,
                "vote_type": v.vote_type,
                "timestamp": v.timestamp.isoformat()
            } for v in decision.votes
        ]
        payload = dict(decision.decision_payload)
        payload["votes"] = votes_data
        if decision.override_reason:
            payload["override_reason"] = {
                "justification": decision.override_reason.justification,
                "referenced_incident_urn": decision.override_reason.referenced_incident_urn
            }

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cio_decisions (
                        decision_id, calculation_id, governance_exception_id, decision_journal_ref,
                        portfolio_snapshot_hash, action_type, target_node_type, target_node_id,
                        decision_payload, cryptographic_signature, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        decision.decision_id,
                        decision.calculation_id,
                        decision.governance_exception_id,
                        decision.decision_journal_ref,
                        decision.portfolio_snapshot_hash,
                        decision.action_type,
                        decision.target_node_type,
                        decision.target_node_id,
                        json.dumps(payload),
                        decision.cryptographic_signature,
                        decision.created_at
                    )
                )
        except psycopg.errors.UniqueViolation as e:
            raise ImmutabilityViolationException("Cannot overwrite an existing CIO decision record.") from e
        except psycopg.errors.RaiseException as e:
            # Check if triggered by check_unique_decision_journal_ref or block_cio_mutation
            err_msg = str(e)
            if "1:1 cardinality constraint violated" in err_msg:
                raise DuplicateJournalRefException(err_msg) from e
            else:
                raise ImmutabilityViolationException(err_msg) from e

    def get_decision_by_id(self, decision_id: str) -> Optional[CIODecisionAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, calculation_id, governance_exception_id, decision_journal_ref,
                       portfolio_snapshot_hash, action_type, target_node_type, target_node_id,
                       decision_payload, cryptographic_signature, created_at
                FROM cio_decisions
                WHERE decision_id = %s
                """,
                (decision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def get_decision_by_journal_ref(self, journal_ref: str) -> Optional[CIODecisionAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, calculation_id, governance_exception_id, decision_journal_ref,
                       portfolio_snapshot_hash, action_type, target_node_type, target_node_id,
                       decision_payload, cryptographic_signature, created_at
                FROM cio_decisions
                WHERE decision_journal_ref = %s
                """,
                (journal_ref,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_aggregate(row)

    def list_decisions(self, limit: int = 50, offset: int = 0) -> List[CIODecisionAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, calculation_id, governance_exception_id, decision_journal_ref,
                       portfolio_snapshot_hash, action_type, target_node_type, target_node_id,
                       decision_payload, cryptographic_signature, created_at
                FROM cio_decisions
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_aggregate(row) for row in rows]

    def save_portfolio_state(self, state: PortfolioStateProjection) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_states (
                        state_id, decision_id, portfolio_tree, created_at
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        state.state_id,
                        state.decision_id,
                        json.dumps(state.portfolio_tree),
                        state.created_at
                    )
                )
        except psycopg.errors.UniqueViolation as e:
            raise ImmutabilityViolationException("Cannot overwrite an existing portfolio state record.") from e
        except psycopg.errors.RaiseException as e:
            raise ImmutabilityViolationException(str(e)) from e

    def get_latest_portfolio_state(self) -> Optional[PortfolioStateProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT state_id, decision_id, portfolio_tree, created_at
                FROM portfolio_states
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            return PortfolioStateProjection(
                state_id=row[0],
                decision_id=row[1],
                portfolio_tree=row[2] if isinstance(row[2], dict) else json.loads(row[2]),
                created_at=row[3]
            )

    def _row_to_aggregate(self, row) -> CIODecisionAggregate:
        payload = row[8] if isinstance(row[8], dict) else json.loads(row[8])
        votes_data = payload.pop("votes", [])
        votes = [
            CommitteeVote(
                voter_id=v["voter_id"],
                vote_type=v["vote_type"],
                timestamp=datetime.fromisoformat(v["timestamp"])
            ) for v in votes_data
        ]
        
        override_reason = None
        override_data = payload.pop("override_reason", None)
        if override_data:
            override_reason = OverrideReason(
                justification=override_data["justification"],
                referenced_incident_urn=override_data.get("referenced_incident_urn")
            )

        return CIODecisionAggregate(
            decision_id=row[0],
            calculation_id=row[1],
            governance_exception_id=row[2],
            decision_journal_ref=row[3],
            portfolio_snapshot_hash=row[4],
            action_type=row[5],
            target_node_type=row[6],
            target_node_id=row[7],
            decision_payload=payload,
            cryptographic_signature=row[9],
            created_at=row[10],
            votes=votes,
            override_reason=override_reason
        )
