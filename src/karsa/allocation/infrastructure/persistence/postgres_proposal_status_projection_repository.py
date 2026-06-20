from typing import Optional, List
from datetime import datetime

from karsa.allocation.domain.model.proposal_status_projection import ProposalStatusProjection
from karsa.allocation.domain.repository.proposal_status_projection_repository import ProposalStatusProjectionRepository


class PostgresProposalStatusProjectionRepository(ProposalStatusProjectionRepository):
    def __init__(self, conn):
        self.conn = conn

    def get_status(self, proposal_id: str) -> Optional[ProposalStatusProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT proposal_id, status, decision_id, decided_at, decided_by, event_sequence
                FROM proposal_status_projection
                WHERE proposal_id = %s
                """,
                (proposal_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_projection(row)

    def list_by_status(self, status: str, limit: int = 50, offset: int = 0) -> List[ProposalStatusProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT proposal_id, status, decision_id, decided_at, decided_by, event_sequence
                FROM proposal_status_projection
                WHERE status = %s
                ORDER BY decided_at DESC NULLS LAST
                LIMIT %s OFFSET %s
                """,
                (status, limit, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_projection(r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ProposalStatusProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT proposal_id, status, decision_id, decided_at, decided_by, event_sequence
                FROM proposal_status_projection
                ORDER BY proposal_id
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            rows = cur.fetchall()
            return [self._row_to_projection(r) for r in rows]

    def upsert_pending(self, proposal_id: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO proposal_status_projection (proposal_id, status, event_sequence)
                VALUES (%s, 'PENDING', %s)
                ON CONFLICT (proposal_id) DO NOTHING
                """,
                (proposal_id, event_sequence)
            )

    def mark_approved(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE proposal_status_projection
                SET status = 'APPROVED', decision_id = %s, decided_by = %s, decided_at = %s, event_sequence = %s
                WHERE proposal_id = %s AND event_sequence < %s
                """,
                (decision_id, decided_by, decided_at, event_sequence, proposal_id, event_sequence)
            )

    def mark_rejected(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE proposal_status_projection
                SET status = 'REJECTED', decision_id = %s, decided_by = %s, decided_at = %s, event_sequence = %s
                WHERE proposal_id = %s AND event_sequence < %s
                """,
                (decision_id, decided_by, decided_at, event_sequence, proposal_id, event_sequence)
            )

    def mark_modified(self, proposal_id: str, decision_id: str, decided_by: str, decided_at: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE proposal_status_projection
                SET status = 'MODIFIED', decision_id = %s, decided_by = %s, decided_at = %s, event_sequence = %s
                WHERE proposal_id = %s AND event_sequence < %s
                """,
                (decision_id, decided_by, decided_at, event_sequence, proposal_id, event_sequence)
            )

    def mark_expired(self, proposal_id: str, decided_at: str, event_sequence: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE proposal_status_projection
                SET status = 'EXPIRED', decided_at = %s, event_sequence = %s
                WHERE proposal_id = %s AND event_sequence < %s
                """,
                (decided_at, event_sequence, proposal_id, event_sequence)
            )

    def _row_to_projection(self, row) -> ProposalStatusProjection:
        return ProposalStatusProjection(
            proposal_id=row[0],
            status=row[1],
            decision_id=row[2],
            decided_at=row[3],
            decided_by=row[4],
            event_sequence=row[5],
        )
