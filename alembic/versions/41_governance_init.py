"""
Alembic migration for Sprint-41 Governance Engine Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '41_governance_init'
down_revision = '40_risk_engine_init'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create block_mutation trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION block_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Governance ledger records are strictly immutable. UPDATE and DELETE operations are prohibited.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 2. Create compliance_policies
    op.execute("""
        CREATE TABLE IF NOT EXISTS compliance_policies (
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
        CREATE UNIQUE INDEX IF NOT EXISTS idx_compliance_policies_urn ON compliance_policies(policy_urn);
    """)

    # 3. Create authorization_policies
    op.execute("""
        CREATE TABLE IF NOT EXISTS authorization_policies (
            policy_id VARCHAR(128) PRIMARY KEY,
            policy_urn VARCHAR(256) NOT NULL UNIQUE,
            state VARCHAR(64) NOT NULL,
            roles_mapping JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL
        );
    """)

    # 4. Create exception_tokens (partitioned by expire_time)
    op.execute("""
        CREATE TABLE IF NOT EXISTS exception_tokens (
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

        CREATE TABLE IF NOT EXISTS exception_tokens_default PARTITION OF exception_tokens DEFAULT;
    """)

    # 5. Create exception_revocations
    op.execute("""
        CREATE TABLE IF NOT EXISTS exception_revocations (
            revocation_id UUID PRIMARY KEY,
            token_hash VARCHAR(64) NOT NULL,
            revoked_by VARCHAR(256) NOT NULL,
            revoked_at TIMESTAMP NOT NULL,
            reason VARCHAR(512)
        );
    """)

    # 6. Create governance_decision_records (partitioned by evaluated_at)
    op.execute("""
        CREATE TABLE IF NOT EXISTS governance_decision_records (
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

        CREATE TABLE IF NOT EXISTS governance_decision_records_default PARTITION OF governance_decision_records DEFAULT;
    """)

    # 7. Create policy_history
    op.execute("""
        CREATE TABLE IF NOT EXISTS policy_history (
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

    # 8. Create risk_state_snapshots
    op.execute("""
        CREATE TABLE IF NOT EXISTS risk_state_snapshots (
            portfolio_snapshot_id VARCHAR(256) PRIMARY KEY,
            risk_metrics JSONB NOT NULL,
            concentration_stats JSONB NOT NULL,
            evaluated_at TIMESTAMP NOT NULL,
            cached_at TIMESTAMP NOT NULL
        );
    """)

    # 9. Bind block_mutation triggers to block UPDATE/DELETE
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_compliance_immutability ON compliance_policies;
        CREATE TRIGGER enforce_compliance_immutability
        BEFORE UPDATE OR DELETE ON compliance_policies
        FOR EACH ROW EXECUTE FUNCTION block_mutation();

        DROP TRIGGER IF EXISTS enforce_auth_immutability ON authorization_policies;
        CREATE TRIGGER enforce_auth_immutability
        BEFORE UPDATE OR DELETE ON authorization_policies
        FOR EACH ROW EXECUTE FUNCTION block_mutation();

        DROP TRIGGER IF EXISTS enforce_exception_immutability ON exception_tokens;
        CREATE TRIGGER enforce_exception_immutability
        BEFORE UPDATE OR DELETE ON exception_tokens
        FOR EACH ROW EXECUTE FUNCTION block_mutation();

        DROP TRIGGER IF EXISTS enforce_revocation_immutability ON exception_revocations;
        CREATE TRIGGER enforce_revocation_immutability
        BEFORE UPDATE OR DELETE ON exception_revocations
        FOR EACH ROW EXECUTE FUNCTION block_mutation();

        DROP TRIGGER IF EXISTS enforce_decision_immutability ON governance_decision_records;
        CREATE TRIGGER enforce_decision_immutability
        BEFORE UPDATE OR DELETE ON governance_decision_records
        FOR EACH ROW EXECUTE FUNCTION block_mutation();

        DROP TRIGGER IF EXISTS enforce_history_immutability ON policy_history;
        CREATE TRIGGER enforce_history_immutability
        BEFORE UPDATE OR DELETE ON policy_history
        FOR EACH ROW EXECUTE FUNCTION block_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_history_immutability ON policy_history;
        DROP TRIGGER IF EXISTS enforce_decision_immutability ON governance_decision_records;
        DROP TRIGGER IF EXISTS enforce_revocation_immutability ON exception_revocations;
        DROP TRIGGER IF EXISTS enforce_exception_immutability ON exception_tokens;
        DROP TRIGGER IF EXISTS enforce_auth_immutability ON authorization_policies;
        DROP TRIGGER IF EXISTS enforce_compliance_immutability ON compliance_policies;

        DROP TABLE IF EXISTS risk_state_snapshots CASCADE;
        DROP TABLE IF EXISTS policy_history CASCADE;
        DROP TABLE IF EXISTS governance_decision_records_default CASCADE;
        DROP TABLE IF EXISTS governance_decision_records CASCADE;
        DROP TABLE IF EXISTS exception_revocations CASCADE;
        DROP TABLE IF EXISTS exception_tokens_default CASCADE;
        DROP TABLE IF EXISTS exception_tokens CASCADE;
        DROP TABLE IF EXISTS authorization_policies CASCADE;
        DROP TABLE IF EXISTS compliance_policies CASCADE;

        DROP FUNCTION IF EXISTS block_mutation();
    """)
