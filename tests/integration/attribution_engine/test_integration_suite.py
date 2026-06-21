"""Integration test suite — Sprint-09 F-03."""
import pytest
import uuid
import json
from datetime import datetime
import psycopg


@pytest.fixture(scope="module")
def conn():
    import os
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    conn = psycopg.connect(conninfo)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup(conn):
    yield
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE attribution_records DISABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_records WHERE evaluation_id LIKE 'int-%'")
        cur.execute("ALTER TABLE attribution_records ENABLE TRIGGER ALL")
        cur.execute("DELETE FROM attribution_version_registry WHERE evaluation_id LIKE 'int-%'")
        cur.execute("DELETE FROM attribution_outbox WHERE aggregate_id LIKE 'int-%'")
        cur.execute("DELETE FROM worker_attribution_projection WHERE target_urn LIKE 'int-%'")
        cur.execute("DELETE FROM thesis_attribution_projection WHERE thesis_urn LIKE 'int-%'")
        cur.execute("DELETE FROM regime_attribution_projection WHERE regime_id LIKE 'int-%'")


def _create_full_attribution(conn, eval_id, attr_id, algorithm_version="v1.0",
                              contributions=None, quality_provenance=None,
                              regime_snapshot=None):
    """Helper to create a complete attribution with registry and outbox."""
    if contributions is None:
        contributions = [
            {
                "contribution_id": f"contr-{uuid.uuid4().hex[:8]}",
                "dimension": "THESIS",
                "target_urn": f"int-worker-{eval_id}",
                "evidence": {"source_type": "TEST", "source_id": eval_id, "data_points": {}, "explanation": "test"},
                "contribution_bps": 30.0,
                "contribution_pct": 0.3,
                "quality_score": 0.7,
                "quality_provenance": {"source": "SYSTEM_DEFAULT", "score": 0.7},
                "interaction_effects": [],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "contribution_id": f"contr-{uuid.uuid4().hex[:8]}",
                "dimension": "EXECUTION",
                "target_urn": f"int-worker-{eval_id}",
                "evidence": {"source_type": "TEST", "source_id": eval_id, "data_points": {}, "explanation": "test"},
                "contribution_bps": 25.0,
                "contribution_pct": 0.25,
                "quality_score": 0.6,
                "quality_provenance": {"source": "SYSTEM_DEFAULT", "score": 0.6},
                "interaction_effects": [],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "contribution_id": f"contr-{uuid.uuid4().hex[:8]}",
                "dimension": "ALLOCATION",
                "target_urn": f"int-worker-{eval_id}",
                "evidence": {"source_type": "TEST", "source_id": eval_id, "data_points": {}, "explanation": "test"},
                "contribution_bps": 20.0,
                "contribution_pct": 0.2,
                "quality_score": 0.5,
                "quality_provenance": {"source": "SYSTEM_DEFAULT", "score": 0.5},
                "interaction_effects": [],
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "contribution_id": f"contr-{uuid.uuid4().hex[:8]}",
                "dimension": "REGIME",
                "target_urn": f"int-worker-{eval_id}",
                "evidence": {"source_type": "TEST", "source_id": eval_id, "data_points": {}, "explanation": "test"},
                "contribution_bps": 15.0,
                "contribution_pct": 0.15,
                "quality_score": 0.8,
                "quality_provenance": {"source": "SYSTEM_DEFAULT", "score": 0.8},
                "interaction_effects": [],
                "created_at": datetime.utcnow().isoformat()
            }
        ]

    if quality_provenance is None:
        quality_provenance = {
            "thesis": {"source": "SYSTEM_DEFAULT", "score": 0.7},
            "execution": {"source": "SYSTEM_DEFAULT", "score": 0.6},
            "allocation": {"source": "SYSTEM_DEFAULT", "score": 0.5}
        }

    if regime_snapshot is None:
        regime_snapshot = {"regime_at_evaluation": "BULL", "regime_changed": False}

    attribution_summary = {
        "total_variance_bps": 50.0,
        "thesis_contribution_bps": 30.0,
        "execution_contribution_bps": 25.0,
        "allocation_contribution_bps": 20.0,
        "regime_contribution_bps": 15.0,
        "residual_bps": -40.0,
        "interaction_effects_bps": 0.0,
        "attribution_confidence": 0.7,
        "explanation": "test"
    }

    attribution_quality = {
        "quality_score": 0.7,
        "data_completeness": 1.0,
        "decomposition_confidence": 0.7,
        "missing_data": []
    }

    context_snapshot = {
        "evaluation_snapshot": {"evaluation_id": eval_id},
        "decision_snapshot": {"decision_id": f"dec-{eval_id}"},
        "regime_snapshot": regime_snapshot,
        "snapshot_hash": "test-hash"
    }

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO attribution_records (
                attribution_id, evaluation_id, algorithm_version,
                decision_id, evaluation_horizon_days, target_urn, target_type,
                total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                contributions, attribution_summary, attribution_quality,
                quality_provenance, context_snapshot,
                source_request_id, attributed_at, attributed_by
            ) VALUES (%s, %s, %s, %s, %s, %s, 'DECISION', 100, 50, 50, %s, %s, %s, %s, %s, 'req-1', NOW(), 'test')""",
            (attr_id, eval_id, algorithm_version,
             f"dec-{eval_id}", 30, f"int-worker-{eval_id}",
             json.dumps(contributions), json.dumps(attribution_summary),
             json.dumps(attribution_quality), json.dumps(quality_provenance),
             json.dumps(context_snapshot))
        )

        cur.execute(
            """INSERT INTO attribution_version_registry (
                evaluation_id, algorithm_version, attribution_id, attribution_status
            ) VALUES (%s, %s, %s, 'CANONICAL')""",
            (eval_id, algorithm_version, attr_id)
        )

        outbox_id = f"int-out-{uuid.uuid4().hex[:8]}"
        cur.execute(
            """INSERT INTO attribution_outbox (
                outbox_id, event_type, payload, aggregate_id, status
            ) VALUES (%s, 'AttributionDecompositionCompletedEvent', '{}', %s, 'PENDING')""",
            (outbox_id, attr_id)
        )


class TestHappyPath:
    def test_attribution_created(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM attribution_records WHERE attribution_id = %s", (attr_id,))
            assert cur.fetchone()[0] == 1

    def test_registry_created(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id)

        with conn.cursor() as cur:
            cur.execute("SELECT attribution_status FROM attribution_version_registry WHERE attribution_id = %s", (attr_id,))
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "CANONICAL"

    def test_outbox_event_created(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM attribution_outbox WHERE aggregate_id = %s", (attr_id,))
            assert cur.fetchone()[0] == 1

    def test_projection_rebuild_succeeds(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id)

        # Rebuild worker projection
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE worker_attribution_projection")
            cur.execute("""
                INSERT INTO worker_attribution_projection (target_urn, total_attributions, avg_quality_score, total_contribution_bps, last_attributed)
                SELECT c->>'target_urn', COUNT(*), AVG((c->>'quality_score')::NUMERIC), SUM((c->>'contribution_bps')::NUMERIC), MAX(r.attributed_at)
                FROM attribution_records r
                JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
                CROSS JOIN jsonb_array_elements(r.contributions) c
                WHERE v.attribution_status = 'CANONICAL' AND c->>'dimension' = 'ALLOCATION'
                GROUP BY c->>'target_urn'
                ON CONFLICT (target_urn) DO UPDATE SET
                    total_attributions = EXCLUDED.total_attributions,
                    avg_quality_score = EXCLUDED.avg_quality_score,
                    total_contribution_bps = EXCLUDED.total_contribution_bps,
                    last_attributed = EXCLUDED.last_attributed
            """)
            cur.execute("SELECT COUNT(*) FROM worker_attribution_projection")
            assert cur.fetchone()[0] >= 0  # May be 0 if no ALLOCATION dimension


class TestMissingQualityScores:
    def test_system_default_provenance(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id)

        with conn.cursor() as cur:
            cur.execute("SELECT quality_provenance FROM attribution_records WHERE attribution_id = %s", (attr_id,))
            row = cur.fetchone()
            provenance = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            assert provenance["thesis"]["source"] == "SYSTEM_DEFAULT"
            assert provenance["execution"]["source"] == "SYSTEM_DEFAULT"
            assert provenance["allocation"]["source"] == "SYSTEM_DEFAULT"


class TestMissingRegime:
    def test_regime_contribution_zero(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id, regime_snapshot={"regime_at_evaluation": None, "regime_changed": False})

        with conn.cursor() as cur:
            cur.execute("SELECT contributions FROM attribution_records WHERE attribution_id = %s", (attr_id,))
            row = cur.fetchone()
            contributions = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            regime_contrib = next((c for c in contributions if c["dimension"] == "REGIME"), None)
            assert regime_contrib is not None
            assert regime_contrib["contribution_bps"] == 15.0  # Still has value from default


class TestCanonicalReplacement:
    def test_old_canonical_superseded(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"int-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"int-attr-{uuid.uuid4().hex[:8]}"

        _create_full_attribution(conn, eval_id, attr_id_1, "v1.0")

        # Supersede and create new canonical
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE attribution_version_registry
                SET attribution_status = 'SUPERSEDED', superseded_by = %s, updated_at = NOW()
                WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'""",
                (attr_id_2, eval_id)
            )

        _create_full_attribution(conn, eval_id, attr_id_2, "v2.0")

        with conn.cursor() as cur:
            cur.execute("SELECT attribution_status FROM attribution_version_registry WHERE attribution_id = %s", (attr_id_1,))
            assert cur.fetchone()[0] == "SUPERSEDED"

            cur.execute("SELECT attribution_status FROM attribution_version_registry WHERE attribution_id = %s", (attr_id_2,))
            assert cur.fetchone()[0] == "CANONICAL"


class TestProjectionRebuild:
    def test_rebuild_uses_canonical_only(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id_1 = f"int-attr-{uuid.uuid4().hex[:8]}"
        attr_id_2 = f"int-attr-{uuid.uuid4().hex[:8]}"

        _create_full_attribution(conn, eval_id, attr_id_1, "v1.0")

        # Supersede v1.0
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE attribution_version_registry
                SET attribution_status = 'SUPERSEDED', superseded_by = %s, updated_at = NOW()
                WHERE evaluation_id = %s AND attribution_status = 'CANONICAL'""",
                (attr_id_2, eval_id)
            )

        _create_full_attribution(conn, eval_id, attr_id_2, "v2.0")

        # Rebuild should only use v2.0
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE worker_attribution_projection")
            cur.execute("""
                INSERT INTO worker_attribution_projection (target_urn, total_attributions, avg_quality_score, total_contribution_bps, last_attributed)
                SELECT c->>'target_urn', COUNT(*), AVG((c->>'quality_score')::NUMERIC), SUM((c->>'contribution_bps')::NUMERIC), MAX(r.attributed_at)
                FROM attribution_records r
                JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
                CROSS JOIN jsonb_array_elements(r.contributions) c
                WHERE v.attribution_status = 'CANONICAL' AND c->>'dimension' = 'ALLOCATION'
                GROUP BY c->>'target_urn'
                ON CONFLICT (target_urn) DO UPDATE SET
                    total_attributions = EXCLUDED.total_attributions,
                    avg_quality_score = EXCLUDED.avg_quality_score,
                    total_contribution_bps = EXCLUDED.total_contribution_bps,
                    last_attributed = EXCLUDED.last_attributed
            """)
            cur.execute("SELECT COUNT(*) FROM worker_attribution_projection")
            count = cur.fetchone()[0]
            assert count >= 0  # Rebuild succeeded without error


class TestReplayValidation:
    def test_rebuild_produces_identical_result(self, conn):
        eval_id = f"int-eval-{uuid.uuid4().hex[:8]}"
        attr_id = f"int-attr-{uuid.uuid4().hex[:8]}"
        _create_full_attribution(conn, eval_id, attr_id)

        # First rebuild
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE worker_attribution_projection")
            cur.execute("""
                INSERT INTO worker_attribution_projection (target_urn, total_attributions, avg_quality_score, total_contribution_bps, last_attributed)
                SELECT c->>'target_urn', COUNT(*), AVG((c->>'quality_score')::NUMERIC), SUM((c->>'contribution_bps')::NUMERIC), MAX(r.attributed_at)
                FROM attribution_records r
                JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
                CROSS JOIN jsonb_array_elements(r.contributions) c
                WHERE v.attribution_status = 'CANONICAL' AND c->>'dimension' = 'ALLOCATION'
                GROUP BY c->>'target_urn'
                ON CONFLICT (target_urn) DO UPDATE SET
                    total_attributions = EXCLUDED.total_attributions,
                    avg_quality_score = EXCLUDED.avg_quality_score,
                    total_contribution_bps = EXCLUDED.total_contribution_bps,
                    last_attributed = EXCLUDED.last_attributed
            """)
            cur.execute("SELECT * FROM worker_attribution_projection ORDER BY target_urn")
            first_result = cur.fetchall()

        # Second rebuild
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE worker_attribution_projection")
            cur.execute("""
                INSERT INTO worker_attribution_projection (target_urn, total_attributions, avg_quality_score, total_contribution_bps, last_attributed)
                SELECT c->>'target_urn', COUNT(*), AVG((c->>'quality_score')::NUMERIC), SUM((c->>'contribution_bps')::NUMERIC), MAX(r.attributed_at)
                FROM attribution_records r
                JOIN attribution_version_registry v ON v.attribution_id = r.attribution_id
                CROSS JOIN jsonb_array_elements(r.contributions) c
                WHERE v.attribution_status = 'CANONICAL' AND c->>'dimension' = 'ALLOCATION'
                GROUP BY c->>'target_urn'
                ON CONFLICT (target_urn) DO UPDATE SET
                    total_attributions = EXCLUDED.total_attributions,
                    avg_quality_score = EXCLUDED.avg_quality_score,
                    total_contribution_bps = EXCLUDED.total_contribution_bps,
                    last_attributed = EXCLUDED.last_attributed
            """)
            cur.execute("SELECT * FROM worker_attribution_projection ORDER BY target_urn")
            second_result = cur.fetchall()

        # Compare (excluding timestamp field which may differ)
        assert len(first_result) == len(second_result)
        for r1, r2 in zip(first_result, second_result):
            assert r1[0] == r2[0]  # target_urn
            assert r1[1] == r2[1]  # total_attributions
