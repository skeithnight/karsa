"""
Alembic migration for Sprint-38 CIO Engine Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '38_cio_engine_init'
down_revision = '37_decision_journal_init'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create partitioned tables and default partitions
    op.execute("""
        CREATE TABLE IF NOT EXISTS cio_decisions (
            decision_id VARCHAR(128) NOT NULL,
            calculation_id VARCHAR(128),
            governance_exception_id VARCHAR(128),
            decision_journal_ref VARCHAR(128) NOT NULL,
            portfolio_snapshot_hash VARCHAR(64) NOT NULL,
            action_type VARCHAR(128) NOT NULL,
            target_node_type VARCHAR(128) NOT NULL,
            target_node_id VARCHAR(128) NOT NULL,
            decision_payload JSONB NOT NULL DEFAULT '{}',
            cryptographic_signature VARCHAR(256) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (decision_id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE TABLE IF NOT EXISTS cio_decisions_default PARTITION OF cio_decisions DEFAULT;

        CREATE TABLE IF NOT EXISTS portfolio_states (
            state_id VARCHAR(128) NOT NULL,
            decision_id VARCHAR(128) NOT NULL,
            portfolio_tree JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (state_id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE TABLE IF NOT EXISTS portfolio_states_default PARTITION OF portfolio_states DEFAULT;
    """)

    # 2. Add global uniqueness trigger for 1:1 cardinality check
    op.execute("""
        CREATE OR REPLACE FUNCTION check_unique_decision_journal_ref()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM cio_decisions
                WHERE decision_journal_ref = NEW.decision_journal_ref
            ) THEN
                RAISE EXCEPTION 'decision_journal_ref already authorizes a CIO decision. 1:1 cardinality constraint violated.';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS enforce_unique_decision_journal_ref ON cio_decisions;
        CREATE TRIGGER enforce_unique_decision_journal_ref
        BEFORE INSERT ON cio_decisions
        FOR EACH ROW EXECUTE FUNCTION check_unique_decision_journal_ref();
    """)

    # 3. Add immutability triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION block_cio_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'CIO records are strictly immutable. UPDATE and DELETE operations are prohibited.';
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS enforce_cio_decisions_immutability ON cio_decisions;
        CREATE TRIGGER enforce_cio_decisions_immutability
        BEFORE UPDATE OR DELETE ON cio_decisions
        FOR EACH ROW EXECUTE FUNCTION block_cio_mutation();

        DROP TRIGGER IF EXISTS enforce_portfolio_states_immutability ON portfolio_states;
        CREATE TRIGGER enforce_portfolio_states_immutability
        BEFORE UPDATE OR DELETE ON portfolio_states
        FOR EACH ROW EXECUTE FUNCTION block_cio_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_portfolio_states_immutability ON portfolio_states;
        DROP TRIGGER IF EXISTS enforce_cio_decisions_immutability ON cio_decisions;
        DROP TRIGGER IF EXISTS enforce_unique_decision_journal_ref ON cio_decisions;
        DROP FUNCTION IF EXISTS block_cio_mutation();
        DROP FUNCTION IF EXISTS check_unique_decision_journal_ref();
        DROP TABLE IF EXISTS portfolio_states DEFAULT;
        DROP TABLE IF EXISTS portfolio_states CASCADE;
        DROP TABLE IF EXISTS cio_decisions DEFAULT;
        DROP TABLE IF EXISTS cio_decisions CASCADE;
    """)
