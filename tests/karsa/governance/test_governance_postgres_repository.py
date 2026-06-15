import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg

from karsa.governance.domain.models import (
    CompliancePolicy, PolicyURN, PolicyScope, PolicyRule, PolicyCondition,
    PolicyLifecycleState, PolicyAction, AuthorizationPolicy, ExceptionToken,
    ExceptionRevocation, GovernanceDecisionRecord, RiskStateSnapshot
)
from karsa.governance.infrastructure.repositories import (
    PostgresCompliancePolicyRepository, PostgresAuthorizationPolicyRepository,
    PostgresExceptionTokenRepository, PostgresExceptionRevocationRepository,
    PostgresGovernanceDecisionRecordRepository, PostgresRiskStateSnapshotRepository
)

@pytest.fixture(scope="module")
def postgres_pool():
    local_conn_str = "postgresql://chaos:chaos@localhost:5432/chaos"
    try:
        with psycopg.connect(local_conn_str) as conn:
            pass
        with ConnectionPool(local_conn_str) as pool:
            yield pool
            return
    except Exception:
        pass

    try:
        with PostgresContainer("postgres:15") as postgres:
            conn_str = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
            with ConnectionPool(conn_str) as pool:
                yield pool
    except Exception as e:
        pytest.skip(f"Could not connect to local Postgres or start Postgres container: {e}")

@pytest.fixture
def clean_db(postgres_pool):
    with postgres_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS policy_history CASCADE;")
            cur.execute("DROP TABLE IF EXISTS governance_decision_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS governance_decision_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS exception_revocations CASCADE;")
            cur.execute("DROP TABLE IF EXISTS exception_tokens_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS exception_tokens CASCADE;")
            cur.execute("DROP TABLE IF EXISTS authorization_policies CASCADE;")
            cur.execute("DROP TABLE IF EXISTS compliance_policies CASCADE;")
            cur.execute("DROP TABLE IF EXISTS risk_state_snapshots CASCADE;")

            cur.execute("""
                CREATE OR REPLACE FUNCTION block_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'Governance ledger records are strictly immutable. UPDATE and DELETE operations are prohibited.';
                END;
                $$ LANGUAGE plpgsql;
            """)

            cur.execute("""
                CREATE TABLE compliance_policies (
                    row_id UUID PRIMARY KEY,
                    policy_id VARCHAR(128) NOT NULL,
                    policy_urn VARCHAR(256) NOT NULL,
                    state VARCHAR(64) NOT NULL,
                    priority INTEGER NOT NULL,
                    scope_type VARCHAR(64) NOT NULL,
                    scope_urn VARCHAR(256) NOT NULL,
                    rules JSONB NOT NULL,
                    signature_block JSONB,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE authorization_policies (
                    policy_id VARCHAR(128) PRIMARY KEY,
                    policy_urn VARCHAR(256) NOT NULL UNIQUE,
                    state VARCHAR(64) NOT NULL,
                    roles_mapping JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE exception_tokens (
                    token_hash VARCHAR(64) NOT NULL,
                    token_urn VARCHAR(256) NOT NULL,
                    order_id VARCHAR(256) NOT NULL,
                    state VARCHAR(64) NOT NULL,
                    target_type VARCHAR(64) NOT NULL,
                    target_urn VARCHAR(256) NOT NULL,
                    limit_parameter VARCHAR(128) NOT NULL,
                    limit_ceiling NUMERIC NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    expire_time TIMESTAMP NOT NULL,
                    cio_signature VARCHAR(256) NOT NULL,
                    compliance_signature VARCHAR(256) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (token_hash, expire_time)
                ) PARTITION BY RANGE (expire_time);

                CREATE TABLE exception_tokens_default PARTITION OF exception_tokens DEFAULT;
            """)

            cur.execute("""
                CREATE TABLE exception_revocations (
                    revocation_id UUID PRIMARY KEY,
                    token_hash VARCHAR(64) NOT NULL,
                    revoked_by VARCHAR(256) NOT NULL,
                    revoked_at TIMESTAMP NOT NULL,
                    reason VARCHAR(512)
                );
            """)

            cur.execute("""
                CREATE TABLE governance_decision_records (
                    decision_id UUID NOT NULL,
                    order_id VARCHAR(256) NOT NULL,
                    decision_outcome VARCHAR(64) NOT NULL,
                    policy_version_urn VARCHAR(256),
                    exception_token_urn VARCHAR(256),
                    portfolio_snapshot_id VARCHAR(256) NOT NULL,
                    risk_evaluation_id VARCHAR(256) NOT NULL,
                    evaluated_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (decision_id, evaluated_at)
                ) PARTITION BY RANGE (evaluated_at);

                CREATE TABLE governance_decision_records_default PARTITION OF governance_decision_records DEFAULT;
            """)

            cur.execute("""
                CREATE TABLE policy_history (
                    history_id UUID PRIMARY KEY,
                    policy_row_id UUID NOT NULL REFERENCES compliance_policies(row_id),
                    policy_version_urn VARCHAR(256) NOT NULL,
                    from_state VARCHAR(64) NOT NULL,
                    to_state VARCHAR(64) NOT NULL,
                    transition_reason VARCHAR(512),
                    signature_block JSONB,
                    transitioned_by VARCHAR(256) NOT NULL,
                    transitioned_at TIMESTAMP NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE risk_state_snapshots (
                    portfolio_snapshot_id VARCHAR(256) PRIMARY KEY,
                    risk_metrics JSONB NOT NULL,
                    concentration_stats JSONB NOT NULL,
                    evaluated_at TIMESTAMP NOT NULL,
                    cached_at TIMESTAMP NOT NULL
                );
            """)

            cur.execute("""
                CREATE TRIGGER enforce_compliance_immutability BEFORE UPDATE OR DELETE ON compliance_policies
                FOR EACH ROW EXECUTE FUNCTION block_mutation();

                CREATE TRIGGER enforce_auth_immutability BEFORE UPDATE OR DELETE ON authorization_policies
                FOR EACH ROW EXECUTE FUNCTION block_mutation();

                CREATE TRIGGER enforce_exception_immutability BEFORE UPDATE OR DELETE ON exception_tokens
                FOR EACH ROW EXECUTE FUNCTION block_mutation();

                CREATE TRIGGER enforce_revocation_immutability BEFORE UPDATE OR DELETE ON exception_revocations
                FOR EACH ROW EXECUTE FUNCTION block_mutation();

                CREATE TRIGGER enforce_decision_immutability BEFORE UPDATE OR DELETE ON governance_decision_records
                FOR EACH ROW EXECUTE FUNCTION block_mutation();

                CREATE TRIGGER enforce_history_immutability BEFORE UPDATE OR DELETE ON policy_history
                FOR EACH ROW EXECUTE FUNCTION block_mutation();
            """)

def test_postgres_compliance_policy_repository(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        repo = PostgresCompliancePolicyRepository(conn)
        policy = CompliancePolicy(
            policy_id="pol-1",
            policy_urn=PolicyURN("budget", "cost_limit", "1.0.0"),
            scope=PolicyScope("PORTFOLIO", "urn:karsa:portfolio:1"),
            rules=[
                PolicyRule(
                    condition=PolicyCondition("portfolio_var_95", "LESS_THAN_OR_EQUAL", "0.05"),
                    action=PolicyAction.DENY
                )
            ]
        )
        repo.save(policy)
        
        loaded = repo.find_by_id("pol-1")
        assert loaded is not None
        assert loaded.policy_urn.to_string() == "urn:karsa:policy:budget:cost_limit:1.0.0"
        assert loaded.scope.target_urn == "urn:karsa:portfolio:1"
        assert len(loaded.rules) == 1
        assert loaded.rules[0].condition.attribute == "portfolio_var_95"

        # Try to update (should fail due to block_mutation trigger)
        with pytest.raises(psycopg.errors.RaiseException):
            with conn.cursor() as cur:
                cur.execute("UPDATE compliance_policies SET priority = 200 WHERE policy_id = 'pol-1';")

def test_postgres_authorization_policy_repository(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        repo = PostgresAuthorizationPolicyRepository(conn)
        policy = AuthorizationPolicy(
            policy_id="auth-1",
            policy_urn="urn:karsa:auth-policy:standard:1.0.0",
            roles_mapping=[{"role": "CIO", "public_key_hex": "abcd"}]
        )
        repo.save(policy)

        loaded = repo.find_active_policy()
        assert loaded is not None
        assert loaded.policy_id == "auth-1"
        assert loaded.roles_mapping[0]["role"] == "CIO"

        with pytest.raises(psycopg.errors.RaiseException):
            with conn.cursor() as cur:
                cur.execute("DELETE FROM authorization_policies;")

def test_postgres_exception_token_repository(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        repo = PostgresExceptionTokenRepository(conn)
        token = ExceptionToken(
            token_hash="hash123",
            token_urn="urn:karsa:exception:hash123",
            order_id="urn:karsa:execution:record:order1",
            state="ACTIVE",
            target_type="PORTFOLIO",
            target_urn="urn:karsa:portfolio:1",
            limit_parameter="portfolio_var_95",
            limit_ceiling=0.08,
            start_time=datetime.now(timezone.utc),
            expire_time=datetime.now(timezone.utc) + timedelta(hours=2),
            cio_signature="ciosig",
            compliance_signature="compsig"
        )
        repo.save(token)

        loaded = repo.find_by_hash("hash123")
        assert loaded is not None
        assert loaded.order_id == "urn:karsa:execution:record:order1"
        assert loaded.limit_ceiling == 0.08

        loaded_active = repo.find_active_by_order_id("urn:karsa:execution:record:order1")
        assert loaded_active is not None

def test_postgres_exception_revocation_repository(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        repo = PostgresExceptionRevocationRepository(conn)
        rev = ExceptionRevocation(
            revocation_id=str(uuid.uuid4()),
            token_hash="hash123",
            revoked_by="urn:karsa:agent:comp",
            revoked_at=datetime.now(timezone.utc),
            reason="Compromised key"
        )
        repo.save(rev)

        loaded = repo.find_by_token_hash("hash123")
        assert loaded is not None
        assert loaded.reason == "Compromised key"

def test_postgres_governance_decision_repository(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        repo = PostgresGovernanceDecisionRecordRepository(conn)
        dec = GovernanceDecisionRecord(
            decision_id=str(uuid.uuid4()),
            order_id="order1",
            decision_outcome="ALLOW_VIA_EXCEPTION",
            policy_version_urn="urn:karsa:policy:budget:cost_limit:1.0.0",
            exception_token_urn="urn:karsa:exception:hash123",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
            risk_evaluation_id="eval1"
        )
        repo.save(dec)

        loaded = repo.find_by_id(dec.decision_id)
        assert loaded is not None
        assert loaded.decision_outcome == "ALLOW_VIA_EXCEPTION"
        assert loaded.portfolio_snapshot_id == "urn:karsa:portfolio:snapshot:1"
        assert loaded.risk_evaluation_id == "eval1"

def test_postgres_risk_state_snapshot_repository(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        repo = PostgresRiskStateSnapshotRepository(conn)
        snap = RiskStateSnapshot(
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
            risk_metrics={"var_95": 0.04},
            concentration_stats={"hhi": 0.12}
        )
        repo.save(snap)

        loaded = repo.find_by_snapshot_id("urn:karsa:portfolio:snapshot:1")
        assert loaded is not None
        assert loaded.risk_metrics["var_95"] == 0.04
        assert loaded.concentration_stats["hhi"] == 0.12

def test_postgres_repositories_edge_cases(postgres_pool, clean_db):
    with postgres_pool.connection() as conn:
        # 1. CompliancePolicy Repository
        policy_repo = PostgresCompliancePolicyRepository(conn)
        assert policy_repo.find_by_id("non-existent") is None
        assert policy_repo.find_latest_by_urn(PolicyURN("a", "b", "1.0.0")) is None
        assert policy_repo.find_by_urn(PolicyURN("a", "b", "1.0.0")) is None
        assert policy_repo.find_active_for_scope("PORTFOLIO", "urn:x") == []

        # Save a policy with a rule having NO condition
        policy = CompliancePolicy(
            policy_id="pol-no-cond",
            policy_urn=PolicyURN("budget", "nocond", "1.0.0"),
            scope=PolicyScope("PORTFOLIO", "*"),
            rules=[
                PolicyRule(
                    condition=None,
                    action=PolicyAction.ALLOW
                )
            ]
        )
        policy_repo.save(policy)
        loaded = policy_repo.find_by_id("pol-no-cond")
        assert loaded is not None
        assert loaded.rules[0].condition is None

        # 2. AuthorizationPolicy Repository
        auth_repo = PostgresAuthorizationPolicyRepository(conn)
        assert auth_repo.find_by_id("non-existent") is None
        assert auth_repo.find_by_urn("non-existent-urn") is None
        assert auth_repo.find_active_policy() is None

        # Save and query by id and urn
        auth_p = AuthorizationPolicy(
            policy_id="auth-test",
            policy_urn="urn:auth-test",
            roles_mapping=[]
        )
        auth_repo.save(auth_p)
        assert auth_repo.find_by_id("auth-test") is not None
        assert auth_repo.find_by_urn("urn:auth-test") is not None

        # 3. ExceptionToken Repository
        token_repo = PostgresExceptionTokenRepository(conn)
        assert token_repo.find_by_hash("non-existent") is None
        assert token_repo.find_active_by_order_id("non-existent") is None

        # 4. ExceptionRevocation Repository
        rev_repo = PostgresExceptionRevocationRepository(conn)
        assert rev_repo.find_by_token_hash("non-existent") is None

        # 5. GovernanceDecisionRecord Repository
        dec_repo = PostgresGovernanceDecisionRecordRepository(conn)
        assert dec_repo.find_by_id(str(uuid.uuid4())) is None

        # 6. RiskStateSnapshot Repository
        snap_repo = PostgresRiskStateSnapshotRepository(conn)
        assert snap_repo.find_by_snapshot_id("non-existent") is None
