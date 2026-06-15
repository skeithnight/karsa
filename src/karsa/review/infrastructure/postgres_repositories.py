from datetime import timezone
from typing import Optional, List, Dict, Any
from karsa.review.domain.models import ReviewSession, ReviewRecord, PostMortemRecord
from karsa.review.domain.value_objects import (
    DecisionQualityAssessment,
    FailureClassification,
    SuccessClassification,
    ImprovementRecommendation
)
from karsa.review.domain.repositories import (
    ReviewSessionRepository,
    ReviewRecordRepository,
    PostMortemRecordRepository
)
from karsa.review.infrastructure.repositories_batch2 import ConcurrencyConflictError


class PostgresReviewSessionRepository(ReviewSessionRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, session: ReviewSession) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT aggregate_version FROM review_sessions WHERE session_id = %s",
                (session.session_id,)
            )
            row = cur.fetchone()
            if row:
                existing_ver = row[0]
                if existing_ver != session.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing_ver}, got {session.aggregate_version - 1}"
                    )
                cur.execute(
                    """
                    UPDATE review_sessions
                    SET session_urn = %s, horizon_start = %s, horizon_end = %s,
                        raw_input_manifest_hash = %s, status = %s, aggregate_version = %s
                    WHERE session_id = %s
                    """,
                    (
                        session.session_urn,
                        session.horizon_start,
                        session.horizon_end,
                        session.raw_input_manifest_hash,
                        session.status,
                        session.aggregate_version,
                        session.session_id
                    )
                )
            else:
                cur.execute(
                    """
                    INSERT INTO review_sessions (
                        session_id, session_urn, horizon_start, horizon_end,
                        raw_input_manifest_hash, status, aggregate_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session.session_id,
                        session.session_urn,
                        session.horizon_start,
                        session.horizon_end,
                        session.raw_input_manifest_hash,
                        session.status,
                        session.aggregate_version
                    )
                )

    def find_by_id(self, session_id: str) -> Optional[ReviewSession]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, session_urn, horizon_start, horizon_end,
                       raw_input_manifest_hash, status, aggregate_version
                FROM review_sessions WHERE session_id = %s
                """,
                (session_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ReviewSession(
                session_id=str(row[0]),
                session_urn=row[1],
                horizon_start=row[2].replace(tzinfo=timezone.utc),
                horizon_end=row[3].replace(tzinfo=timezone.utc),
                raw_input_manifest_hash=row[4],
                status=row[5],
                aggregate_version=row[6]
            )

    def find_by_urn(self, session_urn: str) -> Optional[ReviewSession]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, session_urn, horizon_start, horizon_end,
                       raw_input_manifest_hash, status, aggregate_version
                FROM review_sessions WHERE session_urn = %s
                """,
                (session_urn,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ReviewSession(
                session_id=str(row[0]),
                session_urn=row[1],
                horizon_start=row[2].replace(tzinfo=timezone.utc),
                horizon_end=row[3].replace(tzinfo=timezone.utc),
                raw_input_manifest_hash=row[4],
                status=row[5],
                aggregate_version=row[6]
            )


class PostgresReviewRecordRepository(ReviewRecordRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, record: ReviewRecord) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT aggregate_version FROM review_records WHERE record_id = %s",
                (record.record_id,)
            )
            row = cur.fetchone()
            if row:
                existing_ver = row[0]
                if existing_ver != record.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing_ver}, got {record.aggregate_version - 1}"
                    )
                cur.execute(
                    """
                    UPDATE review_records
                    SET is_active = %s, superseded_by_version = %s,
                        invalidated_by_version = %s, aggregate_version = %s
                    WHERE record_id = %s
                    """,
                    (
                        record.is_active,
                        record.superseded_by_version,
                        record.invalidated_by_version,
                        record.aggregate_version,
                        record.record_id
                    )
                )
            else:
                cur.execute(
                    """
                    INSERT INTO review_records (
                        record_id, record_urn, session_urn, decision_id, worker_urn,
                        review_methodology_urn, review_policy_hash, review_prompt_version,
                        reviewer_model_version, review_methodology_manifest_hash,
                        outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                        is_active, superseded_by_version, invalidated_by_version,
                        reviewed_at, review_version, aggregate_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.record_id,
                        record.record_urn,
                        record.session_urn,
                        record.decision_id,
                        record.worker_urn,
                        record.review_methodology_urn,
                        record.review_policy_hash,
                        record.review_prompt_version,
                        record.reviewer_model_version,
                        record.review_methodology_manifest_hash,
                        record.decision_quality.outcome_independent_score,
                        record.decision_quality.outcome_dependent_score,
                        record.decision_quality.hindsight_bias_deviation,
                        record.is_active,
                        record.superseded_by_version,
                        record.invalidated_by_version,
                        record.reviewed_at,
                        record.review_version,
                        record.aggregate_version
                    )
                )

    def _row_to_record(self, row) -> ReviewRecord:
        dq = DecisionQualityAssessment(
            outcome_independent_score=float(row[10]),
            outcome_dependent_score=float(row[11]),
            hindsight_bias_deviation=float(row[12])
        )
        return ReviewRecord(
            record_id=str(row[0]),
            record_urn=row[1],
            session_urn=row[2],
            decision_id=row[3],
            worker_urn=row[4],
            review_methodology_urn=row[5],
            review_policy_hash=row[6],
            review_prompt_version=row[7],
            reviewer_model_version=row[8],
            review_methodology_manifest_hash=row[9],
            decision_quality=dq,
            reviewed_at=row[16].replace(tzinfo=timezone.utc),
            review_version=row[17],
            is_active=row[13],
            superseded_by_version=row[14],
            invalidated_by_version=row[15],
            aggregate_version=row[18]
        )

    def find_by_id(self, record_id: str) -> Optional[ReviewRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                       review_methodology_urn, review_policy_hash, review_prompt_version,
                       reviewer_model_version, review_methodology_manifest_hash,
                       outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                       is_active, superseded_by_version, invalidated_by_version,
                       reviewed_at, review_version, aggregate_version
                FROM review_records WHERE record_id = %s
                """,
                (record_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def find_by_urn(self, record_urn: str) -> Optional[ReviewRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                       review_methodology_urn, review_policy_hash, review_prompt_version,
                       reviewer_model_version, review_methodology_manifest_hash,
                       outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                       is_active, superseded_by_version, invalidated_by_version,
                       reviewed_at, review_version, aggregate_version
                FROM review_records WHERE record_urn = %s
                """,
                (record_urn,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def find_active_by_worker(self, worker_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
        with self.conn.cursor() as cur:
            if cursor:
                cur.execute(
                    """
                    SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                           review_methodology_urn, review_policy_hash, review_prompt_version,
                           reviewer_model_version, review_methodology_manifest_hash,
                           outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                           is_active, superseded_by_version, invalidated_by_version,
                           reviewed_at, review_version, aggregate_version
                    FROM review_records
                    WHERE worker_urn = %s AND is_active = TRUE AND record_urn > %s
                    ORDER BY record_urn ASC LIMIT %s
                    """,
                    (worker_urn, cursor, limit)
                )
            else:
                cur.execute(
                    """
                    SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                           review_methodology_urn, review_policy_hash, review_prompt_version,
                           reviewer_model_version, review_methodology_manifest_hash,
                           outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                           is_active, superseded_by_version, invalidated_by_version,
                           reviewed_at, review_version, aggregate_version
                    FROM review_records
                    WHERE worker_urn = %s AND is_active = TRUE
                    ORDER BY record_urn ASC LIMIT %s
                    """,
                    (worker_urn, limit)
                )
            rows = cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[ReviewRecord]:
        with self.conn.cursor() as cur:
            if cursor:
                cur.execute(
                    """
                    SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                           review_methodology_urn, review_policy_hash, review_prompt_version,
                           reviewer_model_version, review_methodology_manifest_hash,
                           outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                           is_active, superseded_by_version, invalidated_by_version,
                           reviewed_at, review_version, aggregate_version
                    FROM review_records
                    WHERE session_urn = %s AND record_urn > %s
                    ORDER BY record_urn ASC LIMIT %s
                    """,
                    (session_urn, cursor, limit)
                )
            else:
                cur.execute(
                    """
                    SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                           review_methodology_urn, review_policy_hash, review_prompt_version,
                           reviewer_model_version, review_methodology_manifest_hash,
                           outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                           is_active, superseded_by_version, invalidated_by_version,
                           reviewed_at, review_version, aggregate_version
                    FROM review_records
                    WHERE session_urn = %s
                    ORDER BY record_urn ASC LIMIT %s
                    """,
                    (session_urn, limit)
                )
            rows = cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    def find_review_lineage(self, start_record_urn: str) -> List[ReviewRecord]:
        start = self.find_by_urn(start_record_urn)
        if not start:
            return []
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT record_id, record_urn, session_urn, decision_id, worker_urn,
                       review_methodology_urn, review_policy_hash, review_prompt_version,
                       reviewer_model_version, review_methodology_manifest_hash,
                       outcome_independent_score, outcome_dependent_score, hindsight_bias_deviation,
                       is_active, superseded_by_version, invalidated_by_version,
                       reviewed_at, review_version, aggregate_version
                FROM review_records
                WHERE decision_id = %s AND worker_urn = %s
                """,
                (start.decision_id, start.worker_urn)
            )
            rows = cur.fetchall()
            all_recs = [self._row_to_record(r) for r in rows]
            from karsa.review.domain.lineage import reconstruct_review_lineage
            return reconstruct_review_lineage(all_recs, start_record_urn)


class PostgresPostMortemRecordRepository(PostMortemRecordRepository):
    def __init__(self, conn):
        self.conn = conn

    def save(self, postmortem: PostMortemRecord) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT aggregate_version FROM postmortem_records WHERE postmortem_id = %s",
                (postmortem.postmortem_id,)
            )
            row = cur.fetchone()
            if row:
                existing_ver = row[0]
                if existing_ver != postmortem.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"OCC Conflict: Expected version {existing_ver}, got {postmortem.aggregate_version - 1}"
                    )
                cur.execute(
                    """
                    UPDATE postmortem_records
                    SET is_active = %s, superseded_by_version = %s,
                        invalidated_by_version = %s, aggregate_version = %s
                    WHERE postmortem_id = %s
                    """,
                    (
                        postmortem.is_active,
                        postmortem.superseded_by_version,
                        postmortem.invalidated_by_version,
                        postmortem.aggregate_version,
                        postmortem.postmortem_id
                    )
                )
            else:
                cur.execute(
                    """
                    INSERT INTO postmortem_records (
                        postmortem_id, postmortem_urn, session_urn, decision_id,
                        consensus_methodology_urn, consensus_policy_hash, input_review_record_urns,
                        thesis_error, execution_error, timing_error, sizing_error, calibration_error,
                        alpha_generation, execution_efficiency, risk_mitigation,
                        recommendation_code, recommendation_category, recommendation_severity,
                        thesis_refinement_actions, is_active, superseded_by_version, invalidated_by_version,
                        created_at, postmortem_version, aggregate_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        postmortem.postmortem_id,
                        postmortem.postmortem_urn,
                        postmortem.session_urn,
                        postmortem.decision_id,
                        postmortem.consensus_methodology_urn,
                        postmortem.consensus_policy_hash,
                        postmortem.input_review_record_urns,
                        postmortem.failure_classification.thesis_error,
                        postmortem.failure_classification.execution_error,
                        postmortem.failure_classification.timing_error,
                        postmortem.failure_classification.sizing_error,
                        postmortem.failure_classification.calibration_error,
                        postmortem.success_classification.alpha_generation,
                        postmortem.success_classification.execution_efficiency,
                        postmortem.success_classification.risk_mitigation,
                        postmortem.recommendation.recommendation_code,
                        postmortem.recommendation.recommendation_category,
                        postmortem.recommendation.recommendation_severity,
                        postmortem.recommendation.thesis_refinement_actions,
                        postmortem.is_active,
                        postmortem.superseded_by_version,
                        postmortem.invalidated_by_version,
                        postmortem.created_at,
                        postmortem.postmortem_version,
                        postmortem.aggregate_version
                    )
                )

    def _row_to_pm(self, row) -> PostMortemRecord:
        fc = FailureClassification(
            thesis_error=row[7],
            execution_error=row[8],
            timing_error=row[9],
            sizing_error=row[10],
            calibration_error=row[11]
        )
        sc = SuccessClassification(
            alpha_generation=row[12],
            execution_efficiency=row[13],
            risk_mitigation=row[14]
        )
        rec = ImprovementRecommendation(
            recommendation_code=row[15],
            recommendation_category=row[16],
            recommendation_severity=row[17],
            thesis_refinement_actions=row[18]
        )
        return PostMortemRecord(
            postmortem_id=str(row[0]),
            postmortem_urn=row[1],
            session_urn=row[2],
            decision_id=row[3],
            consensus_methodology_urn=row[4],
            consensus_policy_hash=row[5],
            input_review_record_urns=row[6],
            failure_classification=fc,
            success_classification=sc,
            recommendation=rec,
            created_at=row[22].replace(tzinfo=timezone.utc),
            postmortem_version=row[23],
            is_active=row[19],
            superseded_by_version=row[20],
            invalidated_by_version=row[21],
            aggregate_version=row[24]
        )

    def find_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT postmortem_id, postmortem_urn, session_urn, decision_id,
                       consensus_methodology_urn, consensus_policy_hash, input_review_record_urns,
                       thesis_error, execution_error, timing_error, sizing_error, calibration_error,
                       alpha_generation, execution_efficiency, risk_mitigation,
                       recommendation_code, recommendation_category, recommendation_severity,
                       thesis_refinement_actions, is_active, superseded_by_version, invalidated_by_version,
                       created_at, postmortem_version, aggregate_version
                FROM postmortem_records WHERE postmortem_id = %s
                """,
                (postmortem_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_pm(row)

    def find_by_urn(self, postmortem_urn: str) -> Optional[PostMortemRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT postmortem_id, postmortem_urn, session_urn, decision_id,
                       consensus_methodology_urn, consensus_policy_hash, input_review_record_urns,
                       thesis_error, execution_error, timing_error, sizing_error, calibration_error,
                       alpha_generation, execution_efficiency, risk_mitigation,
                       recommendation_code, recommendation_category, recommendation_severity,
                       thesis_refinement_actions, is_active, superseded_by_version, invalidated_by_version,
                       created_at, postmortem_version, aggregate_version
                FROM postmortem_records WHERE postmortem_urn = %s
                """,
                (postmortem_urn,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_pm(row)

    def find_by_session_paginated(self, session_urn: str, limit: int, cursor: Optional[str] = None) -> List[PostMortemRecord]:
        with self.conn.cursor() as cur:
            if cursor:
                cur.execute(
                    """
                    SELECT postmortem_id, postmortem_urn, session_urn, decision_id,
                           consensus_methodology_urn, consensus_policy_hash, input_review_record_urns,
                           thesis_error, execution_error, timing_error, sizing_error, calibration_error,
                           alpha_generation, execution_efficiency, risk_mitigation,
                           recommendation_code, recommendation_category, recommendation_severity,
                           thesis_refinement_actions, is_active, superseded_by_version, invalidated_by_version,
                           created_at, postmortem_version, aggregate_version
                    FROM postmortem_records
                    WHERE session_urn = %s AND postmortem_urn > %s
                    ORDER BY postmortem_urn ASC LIMIT %s
                    """,
                    (session_urn, cursor, limit)
                )
            else:
                cur.execute(
                    """
                    SELECT postmortem_id, postmortem_urn, session_urn, decision_id,
                           consensus_methodology_urn, consensus_policy_hash, input_review_record_urns,
                           thesis_error, execution_error, timing_error, sizing_error, calibration_error,
                           alpha_generation, execution_efficiency, risk_mitigation,
                           recommendation_code, recommendation_category, recommendation_severity,
                           thesis_refinement_actions, is_active, superseded_by_version, invalidated_by_version,
                           created_at, postmortem_version, aggregate_version
                    FROM postmortem_records
                    WHERE session_urn = %s
                    ORDER BY postmortem_urn ASC LIMIT %s
                    """,
                    (session_urn, limit)
                )
            rows = cur.fetchall()
            return [self._row_to_pm(r) for r in rows]

    def find_postmortem_lineage(self, start_postmortem_urn: str) -> List[PostMortemRecord]:
        start = self.find_by_urn(start_postmortem_urn)
        if not start:
            return []
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT postmortem_id, postmortem_urn, session_urn, decision_id,
                       consensus_methodology_urn, consensus_policy_hash, input_review_record_urns,
                       thesis_error, execution_error, timing_error, sizing_error, calibration_error,
                       alpha_generation, execution_efficiency, risk_mitigation,
                       recommendation_code, recommendation_category, recommendation_severity,
                       thesis_refinement_actions, is_active, superseded_by_version, invalidated_by_version,
                       created_at, postmortem_version, aggregate_version
                FROM postmortem_records
                WHERE decision_id = %s
                """,
                (start.decision_id,)
            )
            rows = cur.fetchall()
            all_pms = [self._row_to_pm(r) for r in rows]
            from karsa.review.domain.lineage import reconstruct_postmortem_lineage
            return reconstruct_postmortem_lineage(all_pms, start_postmortem_urn)
