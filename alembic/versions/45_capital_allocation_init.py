"""
Alembic migration for Sprint-45 Capital Allocation Engine Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '45_capital_allocation_init'
down_revision = '44_review_postmortem_init'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create block_allocation_record_mutation trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION block_allocation_record_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Allocation decision records are immutable and cannot be deleted.';
            ELSIF TG_OP = 'UPDATE' THEN
                -- Verify that immutable fields are not modified
                IF NEW.record_id = OLD.record_id AND
                   NEW.record_urn = OLD.record_urn AND
                   NEW.session_urn = OLD.session_urn AND
                   NEW.worker_urn = OLD.worker_urn AND
                   NEW.decision_id = OLD.decision_id AND
                   NEW.horizon_id = OLD.horizon_id AND
                   NEW.horizon_start = OLD.horizon_start AND
                   NEW.horizon_end = OLD.horizon_end AND
                   NEW.raw_score = OLD.raw_score AND
                   NEW.performance_score = OLD.performance_score AND
                   NEW.attribution_score = OLD.attribution_score AND
                   NEW.review_penalty_multiplier = OLD.review_penalty_multiplier AND
                   NEW.recommended_weight = OLD.recommended_weight AND
                   NEW.recommended_capital_percentage = OLD.recommended_capital_percentage AND
                   NEW.tracking_error_pct = OLD.tracking_error_pct AND
                   NEW.max_drawdown_limit = OLD.max_drawdown_limit AND
                   NEW.allocation_methodology_urn = OLD.allocation_methodology_urn AND
                   NEW.allocation_policy_hash = OLD.allocation_policy_hash AND
                   NEW.allocation_strategy_version = OLD.allocation_strategy_version AND
                   NEW.allocation_manifest_hash = OLD.allocation_manifest_hash AND
                   NEW.calculated_at = OLD.calculated_at AND
                   NEW.allocation_version = OLD.allocation_version AND
                   -- Check is_active transitions only from TRUE to FALSE
                   (NEW.is_active = OLD.is_active OR (OLD.is_active = TRUE AND NEW.is_active = FALSE))
                THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Allocation decision records are immutable. Only deactivation and version lineage updates are allowed.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 2. Create allocation_sessions
    op.execute("""
        CREATE TABLE IF NOT EXISTS allocation_sessions (
            session_id UUID PRIMARY KEY,
            session_urn VARCHAR(256) UNIQUE NOT NULL,
            horizon_id VARCHAR(64) NOT NULL,
            horizon_start TIMESTAMP WITH TIME ZONE NOT NULL,
            horizon_end TIMESTAMP WITH TIME ZONE NOT NULL,
            strategy_key VARCHAR(256) NOT NULL,
            status VARCHAR(64) NOT NULL,
            aggregate_version INTEGER NOT NULL
        );
    """)

    # 3. Create allocation_decision_records (partitioned by calculated_at)
    op.execute("""
        CREATE TABLE IF NOT EXISTS allocation_decision_records (
            record_id UUID NOT NULL,
            record_urn VARCHAR(256) NOT NULL,
            session_urn VARCHAR(256) NOT NULL,
            worker_urn VARCHAR(256) NOT NULL,
            decision_id VARCHAR(256) NOT NULL,
            horizon_id VARCHAR(64) NOT NULL,
            horizon_start TIMESTAMP WITH TIME ZONE NOT NULL,
            horizon_end TIMESTAMP WITH TIME ZONE NOT NULL,
            raw_score DOUBLE PRECISION NOT NULL,
            performance_score DOUBLE PRECISION NOT NULL,
            attribution_score DOUBLE PRECISION NOT NULL,
            review_penalty_multiplier DOUBLE PRECISION NOT NULL,
            recommended_weight DOUBLE PRECISION NOT NULL,
            recommended_capital_percentage DOUBLE PRECISION NOT NULL,
            tracking_error_pct DOUBLE PRECISION NOT NULL,
            max_drawdown_limit DOUBLE PRECISION NOT NULL,
            allocation_methodology_urn VARCHAR(256) NOT NULL,
            allocation_policy_hash VARCHAR(256) NOT NULL,
            allocation_strategy_version VARCHAR(256) NOT NULL,
            allocation_manifest_hash VARCHAR(256) NOT NULL,
            supersedes_record_urn VARCHAR(256),
            invalidates_record_urn VARCHAR(256),
            is_active BOOLEAN NOT NULL,
            superseded_by_version INTEGER,
            invalidated_by_version INTEGER,
            calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            allocation_version INTEGER NOT NULL,
            aggregate_version INTEGER NOT NULL,
            PRIMARY KEY (record_id, calculated_at)
        ) PARTITION BY RANGE (calculated_at);

        CREATE TABLE IF NOT EXISTS allocation_decision_records_default PARTITION OF allocation_decision_records DEFAULT;
    """)

    # 4. Bind triggers to enforce immutability
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_record_immutability ON allocation_decision_records;
        CREATE TRIGGER enforce_record_immutability
        BEFORE UPDATE OR DELETE ON allocation_decision_records
        FOR EACH ROW EXECUTE FUNCTION block_allocation_record_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_record_immutability ON allocation_decision_records;
        DROP TABLE IF EXISTS allocation_decision_records_default CASCADE;
        DROP TABLE IF EXISTS allocation_decision_records CASCADE;
        DROP TABLE IF EXISTS allocation_sessions CASCADE;
        DROP FUNCTION IF EXISTS block_allocation_record_mutation();
    """)
