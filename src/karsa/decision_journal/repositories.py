from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import json
from karsa.decision_journal.models import DecisionJournalAggregate, DecisionRevisionAggregate, DecisionEvidenceAggregate
from karsa.decision_journal.projections import ActiveLeafProjection
from karsa.decision_journal.exceptions import ImmutabilityViolationException, LineageIntegrityException
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.decision_journal.value_objects import (
    PromptReference, DatasetReference, TelemetryReference, ArtifactReference, ReplayMetadata, DecisionContextSnapshot, DecisionEvidence
)

class DecisionJournalRepository(ABC):
    @abstractmethod
    def save_journal(self, journal: DecisionJournalAggregate) -> None:
        pass

    @abstractmethod
    def get_journal_by_id(self, decision_id: str) -> Optional[DecisionJournalAggregate]:
        pass

    @abstractmethod
    def save_revision(self, revision: DecisionRevisionAggregate) -> None:
        pass

    @abstractmethod
    def get_revision_by_id(self, revision_id: str) -> Optional[DecisionRevisionAggregate]:
        pass

    @abstractmethod
    def save_evidence(self, evidence: DecisionEvidenceAggregate) -> None:
        pass

    @abstractmethod
    def get_evidences_by_decision_id(self, decision_id: str) -> List[DecisionEvidenceAggregate]:
        pass

    @abstractmethod
    def get_all_revisions_by_root_id(self, root_decision_id: str) -> List[DecisionRevisionAggregate]:
        pass

class ActiveLeafProjectionRepository(ABC):
    @abstractmethod
    def save_active_leaf(self, projection: ActiveLeafProjection) -> None:
        pass

    @abstractmethod
    def get_active_leaf(self, root_decision_id: str) -> Optional[ActiveLeafProjection]:
        pass

class InMemoryDecisionJournalRepository(DecisionJournalRepository):
    def __init__(self):
        self._journals: Dict[str, DecisionJournalAggregate] = {}
        self._revisions: Dict[str, DecisionRevisionAggregate] = {}
        self._evidences: Dict[str, List[DecisionEvidenceAggregate]] = {}

    def save_journal(self, journal: DecisionJournalAggregate) -> None:
        if journal.decision_id in self._journals:
            raise ImmutabilityViolationException("Cannot overwrite an existing decision journal record.")
        self._journals[journal.decision_id] = journal

    def get_journal_by_id(self, decision_id: str) -> Optional[DecisionJournalAggregate]:
        return self._journals.get(decision_id)

    def save_revision(self, revision: DecisionRevisionAggregate) -> None:
        if revision.revision_id in self._revisions:
            raise ImmutabilityViolationException("Cannot overwrite an existing decision revision record.")
        self._revisions[revision.revision_id] = revision

    def get_revision_by_id(self, revision_id: str) -> Optional[DecisionRevisionAggregate]:
        return self._revisions.get(revision_id)

    def save_evidence(self, evidence: DecisionEvidenceAggregate) -> None:
        if evidence.evidence_id in [e.evidence_id for evs in self._evidences.values() for e in evs]:
            raise ImmutabilityViolationException("Cannot overwrite an existing decision evidence record.")
        self._evidences.setdefault(evidence.decision_id, []).append(evidence)

    def get_evidences_by_decision_id(self, decision_id: str) -> List[DecisionEvidenceAggregate]:
        return self._evidences.get(decision_id, [])

    def get_all_revisions_by_root_id(self, root_decision_id: str) -> List[DecisionRevisionAggregate]:
        return [r for r in self._revisions.values() if r.root_decision_id == root_decision_id]

class InMemoryActiveLeafProjectionRepository(ActiveLeafProjectionRepository):
    def __init__(self):
        self._leaves: Dict[str, ActiveLeafProjection] = {}

    def save_active_leaf(self, projection: ActiveLeafProjection) -> None:
        # OCC Check
        existing = self._leaves.get(projection.root_decision_id)
        if existing:
            if existing.version != projection.version - 1:
                raise ConcurrencyConflictError("OCC conflict: Leaf version mismatch.")
        self._leaves[projection.root_decision_id] = projection

    def get_active_leaf(self, root_decision_id: str) -> Optional[ActiveLeafProjection]:
        return self._leaves.get(root_decision_id)

def snapshot_to_dict(snapshot: DecisionContextSnapshot) -> dict:
    return {
        "prompt_ref": {
            "prompt_id": snapshot.prompt_ref.prompt_id,
            "prompt_hash": snapshot.prompt_ref.prompt_hash,
            "template_urn": snapshot.prompt_ref.template_urn
        },
        "dataset_ref": {
            "dataset_id": snapshot.dataset_ref.dataset_id,
            "dataset_hash": snapshot.dataset_ref.dataset_hash,
            "dataset_urn": snapshot.dataset_ref.dataset_urn
        },
        "telemetry_ref": {
            "telemetry_id": snapshot.telemetry_ref.telemetry_id,
            "telemetry_hash": snapshot.telemetry_ref.telemetry_hash,
            "span_id": snapshot.telemetry_ref.span_id
        },
        "artifact_ref": {
            "artifact_id": snapshot.artifact_ref.artifact_id,
            "artifact_hash": snapshot.artifact_ref.artifact_hash,
            "artifact_urn": snapshot.artifact_ref.artifact_urn
        },
        "replay_metadata": {
            "git_commit": snapshot.replay_metadata.git_commit,
            "runtime_image": snapshot.replay_metadata.runtime_image,
            "seed": snapshot.replay_metadata.seed,
            "temperature": snapshot.replay_metadata.temperature,
            "regime_identifier": snapshot.replay_metadata.regime_identifier,
            "prompt_hash": getattr(snapshot.replay_metadata, "prompt_hash", None),
            "dataset_hash": getattr(snapshot.replay_metadata, "dataset_hash", None),
            "artifact_hash": getattr(snapshot.replay_metadata, "artifact_hash", None)
        }
    }

def dict_to_snapshot(data: dict) -> DecisionContextSnapshot:
    prompt = PromptReference(
        data["prompt_ref"]["prompt_id"],
        data["prompt_ref"]["prompt_hash"],
        data["prompt_ref"]["template_urn"]
    )
    dataset = DatasetReference(
        data["dataset_ref"]["dataset_id"],
        data["dataset_ref"]["dataset_hash"],
        data["dataset_ref"]["dataset_urn"]
    )
    telemetry = TelemetryReference(
        data["telemetry_ref"]["telemetry_id"],
        data["telemetry_ref"]["telemetry_hash"],
        data["telemetry_ref"]["span_id"]
    )
    artifact = ArtifactReference(
        data["artifact_ref"]["artifact_id"],
        data["artifact_ref"]["artifact_hash"],
        data["artifact_ref"]["artifact_urn"]
    )
    replay_meta_data = data["replay_metadata"]
    meta = ReplayMetadata(
        git_commit=replay_meta_data["git_commit"],
        runtime_image=replay_meta_data["runtime_image"],
        seed=replay_meta_data.get("seed"),
        temperature=replay_meta_data.get("temperature"),
        regime_identifier=replay_meta_data.get("regime_identifier"),
        prompt_hash=replay_meta_data.get("prompt_hash"),
        dataset_hash=replay_meta_data.get("dataset_hash"),
        artifact_hash=replay_meta_data.get("artifact_hash")
    )
    return DecisionContextSnapshot(prompt, dataset, telemetry, artifact, meta)

class PostgresDecisionJournalRepository(DecisionJournalRepository):
    def __init__(self, conn):
        self.conn = conn

    def _ensure_journal_partition(self, created_at: datetime, root_decision_id: str) -> None:
        day_str = created_at.strftime("%Y%m%d")
        date_str = created_at.strftime("%Y-%m-%d")
        next_day = created_at + timedelta(days=1)
        next_day_str = next_day.strftime("%Y-%m-%d")
        
        partition_name = f"decision_journals_{day_str}"
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = %s", (partition_name,))
            if not cur.fetchone():
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF decision_journals
                    FOR VALUES FROM ('{date_str} 00:00:00') TO ('{next_day_str} 00:00:00')
                    PARTITION BY HASH (root_decision_id)
                """)
                for i in range(16):
                    sub_partition_name = f"{partition_name}_h{i}"
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {sub_partition_name} PARTITION OF {partition_name}
                        FOR VALUES WITH (MODULUS 16, REMAINDER {i})
                    """)

    def _ensure_revision_partition(self, created_at: datetime, root_decision_id: str) -> None:
        day_str = created_at.strftime("%Y%m%d")
        date_str = created_at.strftime("%Y-%m-%d")
        next_day = created_at + timedelta(days=1)
        next_day_str = next_day.strftime("%Y-%m-%d")
        
        partition_name = f"decision_revisions_{day_str}"
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = %s", (partition_name,))
            if not cur.fetchone():
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF decision_revisions
                    FOR VALUES FROM ('{date_str} 00:00:00') TO ('{next_day_str} 00:00:00')
                    PARTITION BY HASH (root_decision_id)
                """)
                for i in range(16):
                    sub_partition_name = f"{partition_name}_h{i}"
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {sub_partition_name} PARTITION OF {partition_name}
                        FOR VALUES WITH (MODULUS 16, REMAINDER {i})
                    """)

    def _ensure_evidence_partition(self, created_at: datetime) -> None:
        day_str = created_at.strftime("%Y%m%d")
        date_str = created_at.strftime("%Y-%m-%d")
        next_day = created_at + timedelta(days=1)
        next_day_str = next_day.strftime("%Y-%m-%d")
        
        partition_name = f"decision_evidences_{day_str}"
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = %s", (partition_name,))
            if not cur.fetchone():
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF decision_evidences
                    FOR VALUES FROM ('{date_str} 00:00:00') TO ('{next_day_str} 00:00:00')
                """)

    def _setup_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS decision_journals (
                    decision_id VARCHAR(128) NOT NULL,
                    parent_decision_id VARCHAR(128),
                    root_decision_id VARCHAR(128) NOT NULL,
                    proposing_agent_id VARCHAR(128) NOT NULL,
                    signature VARCHAR(256) NOT NULL,
                    thesis_urn VARCHAR(128) NOT NULL,
                    context_hash VARCHAR(64) NOT NULL,
                    context_uri VARCHAR(512) NOT NULL,
                    context_snapshot_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (decision_id, root_decision_id, created_at)
                ) PARTITION BY RANGE (created_at);
                
                CREATE TABLE IF NOT EXISTS decision_revisions (
                    revision_id VARCHAR(128) NOT NULL,
                    parent_decision_id VARCHAR(128) NOT NULL,
                    root_decision_id VARCHAR(128) NOT NULL,
                    proposing_agent_id VARCHAR(128) NOT NULL,
                    signature VARCHAR(256) NOT NULL,
                    correction_reason VARCHAR(512) NOT NULL,
                    context_hash VARCHAR(64) NOT NULL,
                    context_uri VARCHAR(512) NOT NULL,
                    context_snapshot_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (revision_id, root_decision_id, created_at)
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE IF NOT EXISTS decision_evidences (
                    evidence_id VARCHAR(128) NOT NULL,
                    decision_id VARCHAR(128) NOT NULL,
                    attached_by_agent_id VARCHAR(128) NOT NULL,
                    signature VARCHAR(256) NOT NULL,
                    evidence_json JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (evidence_id, created_at)
                ) PARTITION BY RANGE (created_at);
            """)
            # Immutability trigger checks
            cur.execute("""
                CREATE OR REPLACE FUNCTION block_journal_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'Decision Journal records are strictly immutable. UPDATE and DELETE operations are prohibited.';
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS enforce_journal_immutability ON decision_journals;
                CREATE TRIGGER enforce_journal_immutability
                BEFORE UPDATE OR DELETE ON decision_journals
                FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();

                DROP TRIGGER IF EXISTS enforce_revision_immutability ON decision_revisions;
                CREATE TRIGGER enforce_revision_immutability
                BEFORE UPDATE OR DELETE ON decision_revisions
                FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();

                DROP TRIGGER IF EXISTS enforce_evidence_immutability ON decision_evidences;
                CREATE TRIGGER enforce_evidence_immutability
                BEFORE UPDATE OR DELETE ON decision_evidences
                FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();
            """)
        self.conn.commit()

    def save_journal(self, journal: DecisionJournalAggregate) -> None:
        created_at = journal.created_at or datetime.utcnow()
        self._ensure_journal_partition(created_at, journal.decision_id)
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO decision_journals (
                        decision_id, parent_decision_id, root_decision_id, proposing_agent_id, signature, thesis_urn, context_hash, context_uri, context_snapshot_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        journal.decision_id,
                        None,
                        journal.decision_id,
                        journal.proposing_agent_id,
                        journal.signature,
                        journal.thesis_urn,
                        journal.context_hash or "DUMMY_HASH",
                        journal.context_uri or "DUMMY_URI",
                        json.dumps(snapshot_to_dict(journal.context_snapshot)),
                        created_at
                    )
                )
            except Exception as e:
                raise ImmutabilityViolationException(f"Database error writing journal: {str(e)}")

    def get_journal_by_id(self, decision_id: str) -> Optional[DecisionJournalAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT decision_id, proposing_agent_id, signature, thesis_urn, context_hash, context_uri, context_snapshot_json, created_at
                FROM decision_journals
                WHERE decision_id = %s
                """,
                (decision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            
            return DecisionJournalAggregate(
                decision_id=row[0],
                proposing_agent_id=row[1],
                signature=row[2],
                thesis_urn=row[3],
                context_snapshot=dict_to_snapshot(row[6]),
                created_at=row[7],
                context_hash=row[4],
                context_uri=row[5]
            )

    def save_revision(self, revision: DecisionRevisionAggregate) -> None:
        created_at = revision.created_at or datetime.utcnow()
        self._ensure_revision_partition(created_at, revision.root_decision_id)
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO decision_revisions (
                        revision_id, parent_decision_id, root_decision_id, proposing_agent_id, signature, correction_reason, context_hash, context_uri, context_snapshot_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        revision.revision_id,
                        revision.parent_decision_id,
                        revision.root_decision_id,
                        revision.proposing_agent_id,
                        revision.signature,
                        revision.correction_reason,
                        revision.context_hash or "DUMMY_HASH",
                        revision.context_uri or "DUMMY_URI",
                        json.dumps(snapshot_to_dict(revision.context_snapshot)),
                        created_at
                    )
                )
            except Exception as e:
                raise ImmutabilityViolationException(f"Database error writing revision: {str(e)}")

    def get_revision_by_id(self, revision_id: str) -> Optional[DecisionRevisionAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT revision_id, parent_decision_id, root_decision_id, proposing_agent_id, signature, correction_reason, context_hash, context_uri, context_snapshot_json, created_at
                FROM decision_revisions
                WHERE revision_id = %s
                """,
                (revision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            
            return DecisionRevisionAggregate(
                revision_id=row[0],
                parent_decision_id=row[1],
                root_decision_id=row[2],
                proposing_agent_id=row[3],
                signature=row[4],
                correction_reason=row[5],
                context_snapshot=dict_to_snapshot(row[8]),
                created_at=row[9],
                context_hash=row[6],
                context_uri=row[7]
            )

    def save_evidence(self, evidence: DecisionEvidenceAggregate) -> None:
        created_at = evidence.created_at or datetime.utcnow()
        self._ensure_evidence_partition(created_at)
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO decision_evidences (
                        evidence_id, decision_id, attached_by_agent_id, signature, evidence_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        evidence.evidence_id,
                        evidence.decision_id,
                        evidence.attached_by_agent_id,
                        evidence.signature,
                        json.dumps({
                            "evidence_id": evidence.evidence.evidence_id,
                            "description": evidence.evidence.description,
                            "artifact_ref": {
                                "artifact_id": evidence.evidence.artifact_ref.artifact_id,
                                "artifact_hash": evidence.evidence.artifact_ref.artifact_hash,
                                "artifact_urn": evidence.evidence.artifact_ref.artifact_urn
                            },
                            "attached_at": evidence.evidence.attached_at.isoformat()
                        }),
                        created_at
                    )
                )
            except Exception as e:
                raise ImmutabilityViolationException(f"Database error writing evidence: {str(e)}")

    def get_evidences_by_decision_id(self, decision_id: str) -> List[DecisionEvidenceAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT evidence_id, decision_id, attached_by_agent_id, signature, evidence_json, created_at
                FROM decision_evidences
                WHERE decision_id = %s
                """,
                (decision_id,)
            )
            rows = cur.fetchall()
            evidences = []
            for row in rows:
                ev_data = row[4]
                artifact_ref = ArtifactReference(
                    artifact_id=ev_data["artifact_ref"]["artifact_id"],
                    artifact_hash=ev_data["artifact_ref"]["artifact_hash"],
                    artifact_urn=ev_data["artifact_ref"]["artifact_urn"]
                )
                evidence_obj = DecisionEvidence(
                    evidence_id=ev_data["evidence_id"],
                    description=ev_data["description"],
                    artifact_ref=artifact_ref,
                    attached_at=datetime.fromisoformat(ev_data["attached_at"])
                )
                evidences.append(
                    DecisionEvidenceAggregate(
                        evidence_id=row[0],
                        decision_id=row[1],
                        attached_by_agent_id=row[2],
                        signature=row[3],
                        evidence=evidence_obj,
                        created_at=row[5]
                    )
                )
            return evidences

    def get_all_revisions_by_root_id(self, root_decision_id: str) -> List[DecisionRevisionAggregate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT revision_id, parent_decision_id, root_decision_id, proposing_agent_id, signature, correction_reason, context_hash, context_uri, context_snapshot_json, created_at
                FROM decision_revisions
                WHERE root_decision_id = %s
                ORDER BY created_at ASC
                """,
                (root_decision_id,)
            )
            rows = cur.fetchall()
            revisions = []
            for row in rows:
                revisions.append(
                    DecisionRevisionAggregate(
                        revision_id=row[0],
                        parent_decision_id=row[1],
                        root_decision_id=row[2],
                        proposing_agent_id=row[3],
                        signature=row[4],
                        correction_reason=row[5],
                        context_snapshot=dict_to_snapshot(row[8]),
                        created_at=row[9],
                        context_hash=row[6],
                        context_uri=row[7]
                    )
                )
            return revisions

class PostgresActiveLeafProjectionRepository(ActiveLeafProjectionRepository):
    def __init__(self, conn):
        self.conn = conn

    def _setup_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_leaf_projections (
                    root_decision_id VARCHAR(128) PRIMARY KEY,
                    active_leaf_decision_id VARCHAR(128) NOT NULL,
                    version INTEGER NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
        self.conn.commit()

    def save_active_leaf(self, projection: ActiveLeafProjection) -> None:
        with self.conn.cursor() as cur:
            # Check existing for OCC
            cur.execute(
                "SELECT version FROM active_leaf_projections WHERE root_decision_id = %s",
                (projection.root_decision_id,)
            )
            row = cur.fetchone()
            if row:
                existing_version = row[0]
                if existing_version != projection.version - 1:
                    raise ConcurrencyConflictError("OCC conflict: Leaf version mismatch.")
                
                # Update under OCC
                cur.execute(
                    """
                    UPDATE active_leaf_projections
                    SET active_leaf_decision_id = %s, version = %s, updated_at = %s
                    WHERE root_decision_id = %s AND version = %s
                    """,
                    (
                        projection.active_leaf_decision_id,
                        projection.version,
                        projection.updated_at,
                        projection.root_decision_id,
                        existing_version
                    )
                )
                if cur.rowcount == 0:
                    raise ConcurrencyConflictError("OCC conflict: Concurrency update failed.")
            else:
                # Insert if new
                try:
                    cur.execute(
                        """
                        INSERT INTO active_leaf_projections (root_decision_id, active_leaf_decision_id, version, updated_at)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            projection.root_decision_id,
                            projection.active_leaf_decision_id,
                            projection.version,
                            projection.updated_at
                        )
                    )
                except Exception as e:
                    # Catch duplicate key or similar conflicts
                    raise ConcurrencyConflictError(f"OCC conflict: Insert failed: {e}")

    def get_active_leaf(self, root_decision_id: str) -> Optional[ActiveLeafProjection]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT root_decision_id, active_leaf_decision_id, version, updated_at FROM active_leaf_projections WHERE root_decision_id = %s",
                (root_decision_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ActiveLeafProjection(
                root_decision_id=row[0],
                active_leaf_decision_id=row[1],
                version=row[2],
                updated_at=row[3]
            )
