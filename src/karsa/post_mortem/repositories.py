from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import json
import uuid
import copy
import psycopg

from karsa.post_mortem.models import PostMortemRecord, Recommendation
from karsa.post_mortem.exceptions import ImmutabilityViolationException
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding,
)
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

class PostMortemRecordRepository(ABC):
    @abstractmethod
    def save_record(self, record: PostMortemRecord) -> None:
        """Saves a post-mortem record. Raises ImmutabilityViolationException on overwrite or duplicate incident."""
        pass

    @abstractmethod
    def get_record_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        """Retrieves a post-mortem record by its ID."""
        pass

    @abstractmethod
    def get_record_by_incident_ref(self, incident_ref: str) -> Optional[PostMortemRecord]:
        """Retrieves a post-mortem record by its incident reference URN."""
        pass

class RecommendationRepository(ABC):
    @abstractmethod
    def save_recommendation(self, rec: Recommendation) -> None:
        """Saves or updates a recommendation. Raises ConcurrencyConflictError on version mismatch."""
        pass

    @abstractmethod
    def get_recommendation_by_id(self, rec_id: str) -> Optional[Recommendation]:
        """Retrieves a recommendation by its ID."""
        pass

class InMemoryPostMortemRecordRepository(PostMortemRecordRepository):
    def __init__(self):
        self._records: Dict[str, PostMortemRecord] = {}

    def save_record(self, record: PostMortemRecord) -> None:
        if record.postmortem_id in self._records:
            raise ImmutabilityViolationException("Cannot overwrite an existing post-mortem record.")
        
        # Enforce 1:1 incident-to-record cardinality
        for existing in self._records.values():
            if existing.incident_ref.incident_ref == record.incident_ref.incident_ref:
                raise ImmutabilityViolationException(
                    f"Incident reference {record.incident_ref.incident_ref} already has a post-mortem record."
                )

        self._records[record.postmortem_id] = copy.deepcopy(record)

    def get_record_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        rec = self._records.get(postmortem_id)
        if not rec:
            return None
        return copy.deepcopy(rec)

    def get_record_by_incident_ref(self, incident_ref: str) -> Optional[PostMortemRecord]:
        for rec in self._records.values():
            if rec.incident_ref.incident_ref == incident_ref:
                return copy.deepcopy(rec)
        return None

class InMemoryRecommendationRepository(RecommendationRepository):
    def __init__(self):
        self._recommendations: Dict[str, Recommendation] = {}
        self.history: List[Dict[str, Any]] = []

    def save_recommendation(self, rec: Recommendation) -> None:
        existing = self._recommendations.get(rec.recommendation_id)
        if not existing:
            self._recommendations[rec.recommendation_id] = copy.deepcopy(rec)
            # Record transition to PROPOSED
            self.history.append({
                "history_id": f"hist_{uuid.uuid4()}",
                "recommendation_id": rec.recommendation_id,
                "from_state": "None",
                "to_state": rec.state,
                "version": rec.version,
                "transitioned_at": rec.updated_at
            })
        else:
            # Check version for OCC
            expected_old_version = rec.version - 1
            if existing.version != expected_old_version:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict: expected version {expected_old_version}, got {existing.version}."
                )
            
            # Record transition if state changed
            if existing.state != rec.state:
                self.history.append({
                    "history_id": f"hist_{uuid.uuid4()}",
                    "recommendation_id": rec.recommendation_id,
                    "from_state": existing.state,
                    "to_state": rec.state,
                    "version": rec.version,
                    "transitioned_at": rec.updated_at
                })
            
            # Update
            self._recommendations[rec.recommendation_id] = copy.deepcopy(rec)

    def get_recommendation_by_id(self, rec_id: str) -> Optional[Recommendation]:
        rec = self._recommendations.get(rec_id)
        if not rec:
            return None
        return copy.deepcopy(rec)

class PostgresPostMortemRecordRepository(PostMortemRecordRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_record(self, record: PostMortemRecord) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO post_mortem_records (
                        postmortem_id, incident_ref, failure_classification, root_causes, findings, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.postmortem_id,
                        record.incident_ref.incident_ref,
                        json.dumps({
                            "failure_type": record.failure_classification.failure_type,
                            "severity": record.failure_classification.severity,
                            "taxonomy_version": record.failure_classification.taxonomy_version
                        }),
                        json.dumps([
                            {
                                "cause_category": rc.cause_category,
                                "weight": rc.weight,
                                "description": rc.description
                            } for rc in record.root_causes
                        ]),
                        json.dumps({
                            "timeline_events": record.findings.timeline_events,
                            "evidence_uris": record.findings.evidence_uris
                        }),
                        record.created_at
                    )
                )
        except psycopg.errors.UniqueViolation as e:
            raise ImmutabilityViolationException("Post-mortem record already exists or incident reference is already used.") from e
        except psycopg.errors.RaiseException as e:
            raise ImmutabilityViolationException(str(e)) from e

    def get_record_by_id(self, postmortem_id: str) -> Optional[PostMortemRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT postmortem_id, incident_ref, failure_classification, root_causes, findings, created_at
                FROM post_mortem_records
                WHERE postmortem_id = %s
                """,
                (postmortem_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def get_record_by_incident_ref(self, incident_ref: str) -> Optional[PostMortemRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT postmortem_id, incident_ref, failure_classification, root_causes, findings, created_at
                FROM post_mortem_records
                WHERE incident_ref = %s
                """,
                (incident_ref,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def _row_to_record(self, row) -> PostMortemRecord:
        fc_data = row[2] if isinstance(row[2], dict) else json.loads(row[2])
        rc_data = row[3] if isinstance(row[3], list) else json.loads(row[3])
        findings_data = row[4] if isinstance(row[4], dict) else json.loads(row[4])

        fc = FailureClassification(
            failure_type=fc_data["failure_type"],
            severity=fc_data["severity"],
            taxonomy_version=fc_data.get("taxonomy_version", 1)
        )
        rcs = [
            RootCauseContribution(
                cause_category=rc["cause_category"],
                weight=rc["weight"],
                description=rc["description"]
            ) for rc in rc_data
        ]
        findings = PostMortemFinding(
            timeline_events=findings_data["timeline_events"],
            evidence_uris=findings_data["evidence_uris"]
        )

        return PostMortemRecord(
            postmortem_id=row[0],
            incident_ref=IncidentReference(row[1]),
            failure_classification=fc,
            root_causes=rcs,
            findings=findings,
            created_at=row[5]
        )

class PostgresRecommendationRepository(RecommendationRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_recommendation(self, rec: Recommendation) -> None:
        existing = self.get_recommendation_by_id(rec.recommendation_id)
        from_state = "None"
        
        if not existing:
            try:
                with self.conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO post_mortem_recommendations (
                            recommendation_id, postmortem_id, target_context, action_item, parameters, state, version, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            rec.recommendation_id,
                            rec.postmortem_id,
                            rec.target_context,
                            rec.action_item,
                            json.dumps(rec.parameters),
                            rec.state,
                            rec.version,
                            rec.updated_at
                        )
                    )
            except psycopg.errors.UniqueViolation as e:
                raise ConcurrencyConflictError("Recommendation already exists.") from e
        else:
            from_state = existing.state
            expected_old_version = rec.version - 1
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE post_mortem_recommendations
                    SET state = %s, version = %s, updated_at = %s
                    WHERE recommendation_id = %s AND version = %s
                    """,
                    (
                        rec.state,
                        rec.version,
                        rec.updated_at,
                        rec.recommendation_id,
                        expected_old_version
                    )
                )
                if cur.rowcount == 0:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict: Recommendation {rec.recommendation_id} was modified by another transaction."
                    )

        # Record state transition in history if state has changed
        if not existing or existing.state != rec.state:
            history_id = f"hist_{uuid.uuid4()}"
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO recommendation_state_history (
                        history_id, recommendation_id, from_state, to_state, version, transitioned_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        history_id,
                        rec.recommendation_id,
                        from_state,
                        rec.state,
                        rec.version,
                        rec.updated_at
                    )
                )

    def get_recommendation_by_id(self, rec_id: str) -> Optional[Recommendation]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT recommendation_id, postmortem_id, target_context, action_item, parameters, state, version, updated_at
                FROM post_mortem_recommendations
                WHERE recommendation_id = %s
                """,
                (rec_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_recommendation(row)

    def _row_to_recommendation(self, row) -> Recommendation:
        params = row[4] if isinstance(row[4], dict) else json.loads(row[4])
        return Recommendation(
            recommendation_id=row[0],
            postmortem_id=row[1],
            target_context=row[2],
            action_item=row[3],
            parameters=params,
            state=row[5],
            version=row[6],
            updated_at=row[7]
        )
