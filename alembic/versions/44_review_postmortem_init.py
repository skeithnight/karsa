"""
Alembic migration for Sprint-44 Review & Post-Mortem Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '44_review_postmortem_init'
down_revision = '43_performance_init'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create block_review_record_mutation trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION block_review_record_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Review records are immutable and cannot be deleted.';
            ELSIF TG_OP = 'UPDATE' THEN
                -- Allow ONLY updates to is_active (from TRUE to FALSE), superseded_by_version, invalidated_by_version, and aggregate_version
                IF NEW.is_active = FALSE AND OLD.is_active = TRUE AND
                   NEW.record_id = OLD.record_id AND
                   NEW.record_urn = OLD.record_urn AND
                   NEW.session_urn = OLD.session_urn AND
                   NEW.decision_id = OLD.decision_id AND
                   NEW.worker_urn = OLD.worker_urn AND
                   NEW.review_methodology_urn = OLD.review_methodology_urn AND
                   NEW.review_policy_hash = OLD.review_policy_hash AND
                   NEW.review_prompt_version = OLD.review_prompt_version AND
                   NEW.reviewer_model_version = OLD.reviewer_model_version AND
                   NEW.review_methodology_manifest_hash = OLD.review_methodology_manifest_hash AND
                   NEW.outcome_independent_score = OLD.outcome_independent_score AND
                   NEW.outcome_dependent_score = OLD.outcome_dependent_score AND
                   NEW.hindsight_bias_deviation = OLD.hindsight_bias_deviation AND
                   NEW.reviewed_at = OLD.reviewed_at AND
                   NEW.review_version = OLD.review_version AND
                   (NEW.superseded_by_version IS NOT DISTINCT FROM OLD.superseded_by_version OR (OLD.superseded_by_version IS NULL AND NEW.superseded_by_version IS NOT NULL)) AND
                   (NEW.invalidated_by_version IS NOT DISTINCT FROM OLD.invalidated_by_version OR (OLD.invalidated_by_version IS NULL AND NEW.invalidated_by_version IS NOT NULL)) THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Review records are immutable. Only deactivation and version lineage updates are allowed.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 2. Create block_postmortem_record_mutation trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION block_postmortem_record_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Postmortem records are immutable and cannot be deleted.';
            ELSIF TG_OP = 'UPDATE' THEN
                -- Allow ONLY updates to is_active (from TRUE to FALSE), superseded_by_version, invalidated_by_version, and aggregate_version
                IF NEW.is_active = FALSE AND OLD.is_active = TRUE AND
                   NEW.postmortem_id = OLD.postmortem_id AND
                   NEW.postmortem_urn = OLD.postmortem_urn AND
                   NEW.session_urn = OLD.session_urn AND
                   NEW.decision_id = OLD.decision_id AND
                   NEW.consensus_methodology_urn = OLD.consensus_methodology_urn AND
                   NEW.consensus_policy_hash = OLD.consensus_policy_hash AND
                   NEW.input_review_record_urns = OLD.input_review_record_urns AND
                   NEW.thesis_error = OLD.thesis_error AND
                   NEW.execution_error = OLD.execution_error AND
                   NEW.timing_error = OLD.timing_error AND
                   NEW.sizing_error = OLD.sizing_error AND
                   NEW.calibration_error = OLD.calibration_error AND
                   NEW.alpha_generation = OLD.alpha_generation AND
                   NEW.execution_efficiency = OLD.execution_efficiency AND
                   NEW.risk_mitigation = OLD.risk_mitigation AND
                   NEW.recommendation_code = OLD.recommendation_code AND
                   NEW.recommendation_category = OLD.recommendation_category AND
                   NEW.recommendation_severity = OLD.recommendation_severity AND
                   NEW.thesis_refinement_actions = OLD.thesis_refinement_actions AND
                   NEW.created_at = OLD.created_at AND
                   NEW.postmortem_version = OLD.postmortem_version AND
                   (NEW.superseded_by_version IS NOT DISTINCT FROM OLD.superseded_by_version OR (OLD.superseded_by_version IS NULL AND NEW.superseded_by_version IS NOT NULL)) AND
                   (NEW.invalidated_by_version IS NOT DISTINCT FROM OLD.invalidated_by_version OR (OLD.invalidated_by_version IS NULL AND NEW.invalidated_by_version IS NOT NULL)) THEN
                    RETURN NEW;
                ELSE
                    RAISE EXCEPTION 'Postmortem records are immutable. Only deactivation and version lineage updates are allowed.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Create review_sessions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS review_sessions (
            session_id UUID PRIMARY KEY,
            session_urn VARCHAR(256) UNIQUE NOT NULL,
            horizon_start TIMESTAMP NOT NULL,
            horizon_end TIMESTAMP NOT NULL,
            raw_input_manifest_hash VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            aggregate_version INTEGER NOT NULL
        );
    """)

    # 4. Create review_records table (partitioned by reviewed_at)
    op.execute("""
        CREATE TABLE IF NOT EXISTS review_records (
            record_id UUID NOT NULL,
            record_urn VARCHAR(256) NOT NULL,
            session_urn VARCHAR(256) NOT NULL,
            decision_id VARCHAR(256) NOT NULL,
            worker_urn VARCHAR(256) NOT NULL,
            review_methodology_urn VARCHAR(256) NOT NULL,
            review_policy_hash VARCHAR(64) NOT NULL,
            review_prompt_version VARCHAR(64) NOT NULL,
            reviewer_model_version VARCHAR(64) NOT NULL,
            review_methodology_manifest_hash VARCHAR(64) NOT NULL,
            outcome_independent_score NUMERIC(5,4) NOT NULL,
            outcome_dependent_score NUMERIC(5,4) NOT NULL,
            hindsight_bias_deviation NUMERIC(5,4) NOT NULL,
            is_active BOOLEAN NOT NULL,
            superseded_by_version INTEGER,
            invalidated_by_version INTEGER,
            reviewed_at TIMESTAMP NOT NULL,
            review_version INTEGER NOT NULL,
            aggregate_version INTEGER NOT NULL,
            PRIMARY KEY (record_id, reviewed_at)
        ) PARTITION BY RANGE (reviewed_at);

        CREATE TABLE IF NOT EXISTS review_records_default PARTITION OF review_records DEFAULT;
    """)

    # 5. Create postmortem_records table (partitioned by created_at)
    op.execute("""
        CREATE TABLE IF NOT EXISTS postmortem_records (
            postmortem_id UUID NOT NULL,
            postmortem_urn VARCHAR(256) NOT NULL,
            session_urn VARCHAR(256) NOT NULL,
            decision_id VARCHAR(256) NOT NULL,
            consensus_methodology_urn VARCHAR(256) NOT NULL,
            consensus_policy_hash VARCHAR(64) NOT NULL,
            input_review_record_urns TEXT[] NOT NULL,
            thesis_error BOOLEAN NOT NULL,
            execution_error BOOLEAN NOT NULL,
            timing_error BOOLEAN NOT NULL,
            sizing_error BOOLEAN NOT NULL,
            calibration_error BOOLEAN NOT NULL,
            alpha_generation BOOLEAN NOT NULL,
            execution_efficiency BOOLEAN NOT NULL,
            risk_mitigation BOOLEAN NOT NULL,
            recommendation_code VARCHAR(64) NOT NULL,
            recommendation_category VARCHAR(64) NOT NULL,
            recommendation_severity VARCHAR(32) NOT NULL,
            thesis_refinement_actions TEXT[] NOT NULL,
            is_active BOOLEAN NOT NULL,
            superseded_by_version INTEGER,
            invalidated_by_version INTEGER,
            created_at TIMESTAMP NOT NULL,
            postmortem_version INTEGER NOT NULL,
            aggregate_version INTEGER NOT NULL,
            PRIMARY KEY (postmortem_id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE TABLE IF NOT EXISTS postmortem_records_default PARTITION OF postmortem_records DEFAULT;
    """)

    # 6. Bind triggers to enforce immutability
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_review_record_immutability ON review_records;
        CREATE TRIGGER enforce_review_record_immutability
        BEFORE UPDATE OR DELETE ON review_records
        FOR EACH ROW EXECUTE FUNCTION block_review_record_mutation();

        DROP TRIGGER IF EXISTS enforce_postmortem_record_immutability ON postmortem_records;
        CREATE TRIGGER enforce_postmortem_record_immutability
        BEFORE UPDATE OR DELETE ON postmortem_records
        FOR EACH ROW EXECUTE FUNCTION block_postmortem_record_mutation();
    """)


def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_postmortem_record_immutability ON postmortem_records;
        DROP TRIGGER IF EXISTS enforce_review_record_immutability ON review_records;
        DROP TABLE IF EXISTS postmortem_records_default CASCADE;
        DROP TABLE IF EXISTS postmortem_records CASCADE;
        DROP TABLE IF EXISTS review_records_default CASCADE;
        DROP TABLE IF EXISTS review_records CASCADE;
        DROP TABLE IF EXISTS review_sessions CASCADE;
        DROP FUNCTION IF EXISTS block_postmortem_record_mutation();
        DROP FUNCTION IF EXISTS block_review_record_mutation();
    """)
