"""
Alembic migration for Sprint-42 Attribution Engine Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '42_attribution_init'
down_revision = '41_governance_init'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create block_attribution_record_mutation trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION block_attribution_record_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Performance attribution records are immutable and cannot be deleted.';
            ELSIF TG_OP = 'UPDATE' THEN
                -- Allow ONLY updates to is_active (from TRUE to FALSE) and increment of aggregate_version
                IF NEW.is_active = FALSE AND OLD.is_active = TRUE AND
                   NEW.record_id = OLD.record_id AND
                   NEW.session_id = OLD.session_id AND
                   NEW.decision_id = OLD.decision_id AND
                   NEW.thesis_urn = OLD.thesis_urn AND
                   NEW.worker_urn = OLD.worker_urn AND
                   NEW.capability_urn = OLD.capability_urn AND
                   NEW.regime_urn = OLD.regime_urn AND
                   NEW.asset_urn = OLD.asset_urn AND
                   NEW.selection_return = OLD.selection_return AND
                   NEW.allocation_return = OLD.allocation_return AND
                   NEW.execution_return = OLD.execution_return AND
                   NEW.beta_return = OLD.beta_return AND
                   NEW.liquidation_tracking_residual = OLD.liquidation_tracking_residual AND
                   NEW.attribution_version = OLD.attribution_version AND
                   NEW.calculated_at = OLD.calculated_at THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Performance attribution records are immutable. Only is_active may be updated from TRUE to FALSE.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 2. Create attribution_sessions
    op.execute("""
        CREATE TABLE IF NOT EXISTS attribution_sessions (
            session_id UUID PRIMARY KEY,
            horizon_start TIMESTAMP NOT NULL,
            horizon_end TIMESTAMP NOT NULL,
            state VARCHAR(64) NOT NULL,
            compounding_strategy VARCHAR(64) NOT NULL,
            raw_input_manifest_hash VARCHAR(256) NOT NULL,
            aggregate_version INTEGER NOT NULL
        );
    """)

    # 3. Create performance_attribution_records (partitioned by calculated_at)
    op.execute("""
        CREATE TABLE IF NOT EXISTS performance_attribution_records (
            record_id UUID NOT NULL,
            session_id UUID NOT NULL,
            decision_id VARCHAR(256) NOT NULL,
            thesis_urn VARCHAR(256) NOT NULL,
            worker_urn VARCHAR(256) NOT NULL,
            capability_urn VARCHAR(256) NOT NULL,
            regime_urn VARCHAR(256) NOT NULL,
            asset_urn VARCHAR(256) NOT NULL,
            selection_return NUMERIC NOT NULL,
            allocation_return NUMERIC NOT NULL,
            execution_return NUMERIC NOT NULL,
            beta_return NUMERIC NOT NULL,
            liquidation_tracking_residual NUMERIC NOT NULL,
            attribution_version INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL,
            calculated_at TIMESTAMP NOT NULL,
            aggregate_version INTEGER NOT NULL,
            PRIMARY KEY (record_id, calculated_at)
        ) PARTITION BY RANGE (calculated_at);

        CREATE TABLE IF NOT EXISTS performance_attribution_records_default PARTITION OF performance_attribution_records DEFAULT;
    """)

    # 4. Bind triggers to enforce immutability
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_record_immutability ON performance_attribution_records;
        CREATE TRIGGER enforce_record_immutability
        BEFORE UPDATE OR DELETE ON performance_attribution_records
        FOR EACH ROW EXECUTE FUNCTION block_attribution_record_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_record_immutability ON performance_attribution_records;
        DROP TABLE IF EXISTS performance_attribution_records_default CASCADE;
        DROP TABLE IF EXISTS performance_attribution_records CASCADE;
        DROP TABLE IF EXISTS attribution_sessions CASCADE;
        DROP FUNCTION IF EXISTS block_attribution_record_mutation();
    """)
