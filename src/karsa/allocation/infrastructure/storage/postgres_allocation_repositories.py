import psycopg
from typing import Optional, List
from karsa.allocation.domain.models import AllocationSession, AllocationDecisionRecord, ImmutabilityViolationError
from karsa.allocation.domain.repository.allocation_repositories import (
    AllocationSessionRepository,
    AllocationDecisionRecordRepository
)
from karsa.allocation.infrastructure.storage.in_memory_repositories import ConcurrencyConflictError

SELECT_COLUMNS = """
    record_id, record_urn, session_urn, worker_urn, decision_id,
    horizon_id, horizon_start, horizon_end,
    raw_score, performance_score, attribution_score, review_penalty_multiplier,
    recommended_weight, recommended_capital_percentage,
    tracking_error_pct, max_drawdown_limit,
    allocation_methodology_urn, allocation_policy_hash,
    allocation_strategy_version, allocation_manifest_hash,
    supersedes_record_urn, invalidates_record_urn,
    is_active, superseded_by_version, invalidated_by_version,
    calculated_at, allocation_version, aggregate_version
"""

class PostgresAllocationSessionRepository(AllocationSessionRepository):
    def __init__(self, connection):
        self.conn = connection

    def save(self, session: AllocationSession) -> None:
        cur = self.conn.cursor()
        sid = session.session_id
        
        # Check existence and version for OCC
        cur.execute("SELECT aggregate_version FROM allocation_sessions WHERE session_id = %s", (sid,))
        row = cur.fetchone()
        
        if not row:
            # Insert new
            cur.execute(
                """
                INSERT INTO allocation_sessions (
                    session_id, session_urn, horizon_id, horizon_start, 
                    horizon_end, strategy_key, status, aggregate_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sid,
                    session.session_urn,
                    session.horizon.horizon_id,
                    session.horizon.horizon_start,
                    session.horizon.horizon_end,
                    session.strategy_key,
                    session.status,
                    session.aggregate_version
                )
            )
        else:
            # Update with OCC version constraint
            existing_ver = row[0]
            if existing_ver != session.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on session {sid}: expected version {existing_ver}, got {session.aggregate_version}"
                )
                
            cur.execute(
                """
                UPDATE allocation_sessions 
                SET status = %s, aggregate_version = %s
                WHERE session_id = %s AND aggregate_version = %s
                """,
                (
                    session.status,
                    session.aggregate_version,
                    sid,
                    existing_ver
                )
            )
            if cur.rowcount == 0:
                raise ConcurrencyConflictError(f"Concurrency update failed on session {sid}")

    def find_by_urn(self, session_urn: str) -> Optional[AllocationSession]:
        from karsa.allocation.domain.value_objects import PortfolioHorizon
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT session_id, session_urn, horizon_id, horizon_start, 
                   horizon_end, strategy_key, status, aggregate_version
            FROM allocation_sessions WHERE session_urn = %s
            """,
            (session_urn,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return AllocationSession(
            session_id=str(row[0]),
            session_urn=row[1],
            horizon=PortfolioHorizon(
                horizon_id=row[2],
                horizon_start=row[3],
                horizon_end=row[4]
            ),
            strategy_key=row[5],
            status=row[6],
            aggregate_version=row[7]
        )


class PostgresAllocationDecisionRecordRepository(AllocationDecisionRecordRepository):
    def __init__(self, connection):
        self.conn = connection

    def _map_row(self, row) -> AllocationDecisionRecord:
        from karsa.allocation.domain.value_objects import (
            PortfolioHorizon, AllocationScore, RiskBudgetAssignment, AllocationRecommendation
        )
        
        horizon = PortfolioHorizon(
            horizon_id=row[5],
            horizon_start=row[6],
            horizon_end=row[7]
        )
        score = AllocationScore(
            raw_score=row[8],
            performance_score=row[9],
            attribution_score=row[10],
            review_penalty_multiplier=row[11]
        )
        risk = RiskBudgetAssignment(
            tracking_error_pct=row[14],
            max_drawdown_limit=row[15]
        )
        rec = AllocationRecommendation(
            recommended_weight=row[12],
            recommended_capital_percentage=row[13],
            risk_budget=risk
        )
        
        return AllocationDecisionRecord(
            record_id=str(row[0]),
            record_urn=row[1],
            session_urn=row[2],
            worker_urn=row[3],
            decision_id=row[4],
            horizon=horizon,
            allocation_score=score,
            recommendation=rec,
            allocation_methodology_urn=row[16],
            allocation_policy_hash=row[17],
            allocation_strategy_version=row[18],
            allocation_manifest_hash=row[19],
            supersedes_record_urn=row[20],
            invalidates_record_urn=row[21],
            is_active=row[22],
            superseded_by_version=row[23],
            invalidated_by_version=row[24],
            allocated_at=row[25],
            allocation_version=row[26],
            aggregate_version=row[27]
        )

    def save(self, record: AllocationDecisionRecord) -> None:
        cur = self.conn.cursor()
        rid = record.record_id
        
        # Check existence and version for OCC
        cur.execute(
            "SELECT aggregate_version, is_active, raw_score, performance_score, attribution_score, review_penalty_multiplier, recommended_weight, recommended_capital_percentage, tracking_error_pct, max_drawdown_limit, worker_urn, calculated_at, allocation_methodology_urn, allocation_policy_hash, allocation_strategy_version, allocation_manifest_hash FROM allocation_decision_records WHERE record_id = %s",
            (rid,)
        )
        row = cur.fetchone()
        
        if not row:
            # Insert new record
            try:
                cur.execute(
                    """
                    INSERT INTO allocation_decision_records (
                        record_id, record_urn, session_urn, worker_urn, decision_id,
                        horizon_id, horizon_start, horizon_end,
                        raw_score, performance_score, attribution_score, review_penalty_multiplier,
                        recommended_weight, recommended_capital_percentage,
                        tracking_error_pct, max_drawdown_limit,
                        allocation_methodology_urn, allocation_policy_hash,
                        allocation_strategy_version, allocation_manifest_hash,
                        supersedes_record_urn, invalidates_record_urn,
                        is_active, superseded_by_version, invalidated_by_version,
                        calculated_at, allocation_version, aggregate_version
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s
                    )
                    """,
                    (
                        rid, record.record_urn, record.session_urn, record.worker_urn, record.decision_id,
                        record.horizon.horizon_id, record.horizon.horizon_start, record.horizon.horizon_end,
                        record.allocation_score.raw_score, record.allocation_score.performance_score,
                        record.allocation_score.attribution_score, record.allocation_score.review_penalty_multiplier,
                        record.recommendation.recommended_weight, record.recommendation.recommended_capital_percentage,
                        record.recommendation.risk_budget.tracking_error_pct, record.recommendation.risk_budget.max_drawdown_limit,
                        record.allocation_methodology_urn, record.allocation_policy_hash,
                        record.allocation_strategy_version, record.allocation_manifest_hash,
                        record.supersedes_record_urn, record.invalidates_record_urn,
                        record.is_active, record.superseded_by_version, record.invalidated_by_version,
                        record.allocated_at, record.allocation_version, record.aggregate_version
                    )
                )
            except psycopg.Error as e:
                err_msg = str(e)
                if "immutable" in err_msg or "immutable" in err_msg.lower():
                    raise ImmutabilityViolationError(err_msg)
                raise e
        else:
            existing_ver = row[0]
            existing_active = row[1]
            
            # 1. OCC check
            if existing_ver != record.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict on record {rid}: expected version {existing_ver}, got {record.aggregate_version - 1}"
                )
            
            # 2. Immutability check (simulate python-side check for completeness)
            if existing_active is False and record.is_active is True:
                raise ImmutabilityViolationError("Cannot reactivate an inactive record")
                
            # Compare immutable fields
            immutable_values = {
                "raw_score": row[2],
                "performance_score": row[3],
                "attribution_score": row[4],
                "review_penalty_multiplier": row[5],
                "recommended_weight": row[6],
                "recommended_capital_percentage": row[7],
                "tracking_error_pct": row[8],
                "max_drawdown_limit": row[9],
                "worker_urn": row[10],
                "calculated_at": row[11],
                "allocation_methodology_urn": row[12],
                "allocation_policy_hash": row[13],
                "allocation_strategy_version": row[14],
                "allocation_manifest_hash": row[15]
            }
            
            # Convert values to compare correctly
            current_values = {
                "raw_score": record.allocation_score.raw_score,
                "performance_score": record.allocation_score.performance_score,
                "attribution_score": record.allocation_score.attribution_score,
                "review_penalty_multiplier": record.allocation_score.review_penalty_multiplier,
                "recommended_weight": record.recommendation.recommended_weight,
                "recommended_capital_percentage": record.recommendation.recommended_capital_percentage,
                "tracking_error_pct": record.recommendation.risk_budget.tracking_error_pct,
                "max_drawdown_limit": record.recommendation.risk_budget.max_drawdown_limit,
                "worker_urn": record.worker_urn,
                "calculated_at": record.allocated_at,
                "allocation_methodology_urn": record.allocation_methodology_urn,
                "allocation_policy_hash": record.allocation_policy_hash,
                "allocation_strategy_version": record.allocation_strategy_version,
                "allocation_manifest_hash": record.allocation_manifest_hash
            }
            
            for key, val in immutable_values.items():
                curr_val = current_values[key]
                if key == "calculated_at":
                    if abs((val - curr_val).total_seconds()) > 0.001:
                        raise ImmutabilityViolationError(f"Cannot modify immutable field '{key}'")
                elif val != curr_val:
                    raise ImmutabilityViolationError(f"Cannot modify immutable field '{key}'")
            
            # Execute database update
            try:
                cur.execute(
                    """
                    UPDATE allocation_decision_records
                    SET is_active = %s,
                        supersedes_record_urn = %s,
                        invalidates_record_urn = %s,
                        superseded_by_version = %s,
                        invalidated_by_version = %s,
                        aggregate_version = %s
                    WHERE record_id = %s AND aggregate_version = %s
                    """,
                    (
                        record.is_active,
                        record.supersedes_record_urn,
                        record.invalidates_record_urn,
                        record.superseded_by_version,
                        record.invalidated_by_version,
                        record.aggregate_version,
                        rid,
                        existing_ver
                    )
                )
                if cur.rowcount == 0:
                    raise ConcurrencyConflictError(f"Concurrency update failed on record {rid}")
            except psycopg.Error as e:
                err_msg = str(e)
                if "immutable" in err_msg or "immutable" in err_msg.lower():
                    raise ImmutabilityViolationError(err_msg)
                raise e

    def find_by_urn(self, record_urn: str) -> Optional[AllocationDecisionRecord]:
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT {SELECT_COLUMNS} FROM allocation_decision_records WHERE record_urn = %s",
            (record_urn,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._map_row(row)

    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        cur = self.conn.cursor()
        if cursor:
            cur.execute(
                f"SELECT {SELECT_COLUMNS} FROM allocation_decision_records WHERE worker_urn = %s AND is_active = TRUE AND record_urn > %s ORDER BY record_urn ASC LIMIT %s",
                (worker_urn, cursor, limit)
            )
        else:
            cur.execute(
                f"SELECT {SELECT_COLUMNS} FROM allocation_decision_records WHERE worker_urn = %s AND is_active = TRUE ORDER BY record_urn ASC LIMIT %s",
                (worker_urn, limit)
            )
        return [self._map_row(r) for r in cur.fetchall()]

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[AllocationDecisionRecord]:
        cur = self.conn.cursor()
        if cursor:
            cur.execute(
                f"SELECT {SELECT_COLUMNS} FROM allocation_decision_records WHERE session_urn = %s AND record_urn > %s ORDER BY record_urn ASC LIMIT %s",
                (session_urn, cursor, limit)
            )
        else:
            cur.execute(
                f"SELECT {SELECT_COLUMNS} FROM allocation_decision_records WHERE session_urn = %s ORDER BY record_urn ASC LIMIT %s",
                (session_urn, limit)
            )
        return [self._map_row(r) for r in cur.fetchall()]

    def find_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        start_rec = self.find_by_urn(start_record_urn)
        if not start_rec:
            return []
            
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT {SELECT_COLUMNS} FROM allocation_decision_records WHERE worker_urn = %s AND horizon_id = %s",
            (start_rec.worker_urn, start_rec.horizon.horizon_id)
        )
        records = [self._map_row(r) for r in cur.fetchall()]
        
        from karsa.allocation.domain.lineage import reconstruct_allocation_lineage
        return reconstruct_allocation_lineage(records, start_record_urn)

    def find_allocation_lineage(self, start_record_urn: str) -> List[AllocationDecisionRecord]:
        return self.find_lineage(start_record_urn)

    def delete(self, record_id: str) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM allocation_decision_records WHERE record_id = %s", (record_id,))
        except psycopg.Error as e:
            err_msg = str(e)
            if "immutable" in err_msg or "immutable" in err_msg.lower():
                raise ImmutabilityViolationError(err_msg)
            raise e
