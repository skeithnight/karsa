"""
Alembic migration for Sprint-43 Performance Engine Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '43_performance_init'
down_revision = '42_attribution_init'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create block_performance_record_mutation trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION block_performance_record_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Performance evaluation records are immutable and cannot be deleted.';
            ELSIF TG_OP = 'UPDATE' THEN
                -- Allow ONLY updates to is_active (from TRUE to FALSE) and version lineage pointers and increment of aggregate_version
                IF NEW.is_active = FALSE AND OLD.is_active = TRUE AND
                   NEW.record_id = OLD.record_id AND
                   NEW.session_id = OLD.session_id AND
                   NEW.decision_id = OLD.decision_id AND
                   NEW.worker_urn = OLD.worker_urn AND
                   NEW.asset_urn = OLD.asset_urn AND
                   NEW.regime_urn = OLD.regime_urn AND
                   NEW.forecast_probability = OLD.forecast_probability AND
                   NEW.realized_outcome = OLD.realized_outcome AND
                   NEW.brier_score_component = OLD.brier_score_component AND
                   NEW.realized_return = OLD.realized_return AND
                   NEW.evaluation_version = OLD.evaluation_version AND
                   NEW.calculated_at = OLD.calculated_at AND
                   (NEW.superseded_by_version IS NOT DISTINCT FROM OLD.superseded_by_version OR (OLD.superseded_by_version IS NULL AND NEW.superseded_by_version IS NOT NULL)) AND
                   (NEW.invalidated_by_version IS NOT DISTINCT FROM OLD.invalidated_by_version OR (OLD.invalidated_by_version IS NULL AND NEW.invalidated_by_version IS NOT NULL)) THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Performance evaluation records are immutable. Only deactivation and version lineage updates are allowed.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 2. Create performance_sessions
    op.execute("""
        CREATE TABLE IF NOT EXISTS performance_sessions (
            session_id UUID PRIMARY KEY,
            horizon_start TIMESTAMP NOT NULL,
            horizon_end TIMESTAMP NOT NULL,
            state VARCHAR(64) NOT NULL,
            raw_input_manifest_hash VARCHAR(256) NOT NULL,
            aggregate_version INTEGER NOT NULL
        );
    """)

    # 3. Create worker_evaluation_records (partitioned by calculated_at)
    op.execute("""
        CREATE TABLE IF NOT EXISTS worker_evaluation_records (
            record_id UUID NOT NULL,
            session_id UUID NOT NULL,
            decision_id VARCHAR(256) NOT NULL,
            worker_urn VARCHAR(256) NOT NULL,
            asset_urn VARCHAR(256) NOT NULL,
            regime_urn VARCHAR(256) NOT NULL,
            forecast_probability NUMERIC NOT NULL,
            realized_outcome INTEGER NOT NULL,
            brier_score_component NUMERIC NOT NULL,
            realized_return NUMERIC NOT NULL,
            evaluation_version INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL,
            calculated_at TIMESTAMP NOT NULL,
            superseded_by_version INTEGER,
            invalidated_by_version INTEGER,
            aggregate_version INTEGER NOT NULL,
            PRIMARY KEY (record_id, calculated_at)
        ) PARTITION BY RANGE (calculated_at);

        CREATE TABLE IF NOT EXISTS worker_evaluation_records_default PARTITION OF worker_evaluation_records DEFAULT;
    """)

    # 4. Bind triggers to enforce immutability
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_performance_record_immutability ON worker_evaluation_records;
        CREATE TRIGGER enforce_performance_record_immutability
        BEFORE UPDATE OR DELETE ON worker_evaluation_records
        FOR EACH ROW EXECUTE FUNCTION block_performance_record_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_performance_record_immutability ON worker_evaluation_records;
        DROP TABLE IF EXISTS worker_evaluation_records_default CASCADE;
        DROP TABLE IF EXISTS worker_evaluation_records CASCADE;
        DROP TABLE IF EXISTS performance_sessions CASCADE;
        DROP FUNCTION IF EXISTS block_performance_record_mutation();
    """)
