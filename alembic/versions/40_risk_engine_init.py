"""
Alembic migration for Sprint-40 Risk Engine Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '40_risk_engine_init'
down_revision = '38_cio_engine_init'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create tables and partitions
    op.execute("""
        CREATE TABLE IF NOT EXISTS risk_evaluation_records (
            evaluation_id VARCHAR(128) NOT NULL,
            portfolio_snapshot_id VARCHAR(128) NOT NULL,
            model_id VARCHAR(128) NOT NULL,
            model_version VARCHAR(64) NOT NULL,
            methodology_version VARCHAR(64) NOT NULL,
            covariance_version VARCHAR(64) NOT NULL,
            stress_scenario_version VARCHAR(64) NOT NULL,
            regime_state_urn VARCHAR(256) NOT NULL,
            risk_metrics JSONB NOT NULL,
            expected_shortfalls JSONB NOT NULL,
            exposures JSONB NOT NULL,
            concentration_stats JSONB NOT NULL,
            liquidity_metrics JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (evaluation_id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE TABLE IF NOT EXISTS risk_evaluation_records_default PARTITION OF risk_evaluation_records DEFAULT;

        CREATE TABLE IF NOT EXISTS covariance_forecasts (
            forecast_id VARCHAR(128) PRIMARY KEY,
            matrix_urn VARCHAR(256) NOT NULL UNIQUE,
            universe_size INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stress_evaluation_records (
            stress_evaluation_id VARCHAR(128) PRIMARY KEY,
            portfolio_snapshot_id VARCHAR(128) NOT NULL,
            scenario_urn VARCHAR(256) NOT NULL,
            shock_results JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL
        );
    """)

    # 2. Add global uniqueness trigger for 1:1 cardinality check on portfolio_snapshot_id
    op.execute("""
        CREATE OR REPLACE FUNCTION check_unique_portfolio_snapshot_id()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM risk_evaluation_records
                WHERE portfolio_snapshot_id = NEW.portfolio_snapshot_id
            ) THEN
                RAISE EXCEPTION 'portfolio_snapshot_id already has a risk evaluation record. 1:1 cardinality constraint violated.';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS enforce_unique_portfolio_snapshot_id ON risk_evaluation_records;
        CREATE TRIGGER enforce_unique_portfolio_snapshot_id
        BEFORE INSERT ON risk_evaluation_records
        FOR EACH ROW EXECUTE FUNCTION check_unique_portfolio_snapshot_id();
    """)

    # 3. Add immutability triggers to block UPDATE/DELETE on risk tables
    op.execute("""
        CREATE OR REPLACE FUNCTION block_risk_record_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Risk records are strictly immutable. UPDATE and DELETE operations are prohibited.';
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS enforce_risk_eval_immutability ON risk_evaluation_records;
        CREATE TRIGGER enforce_risk_eval_immutability
        BEFORE UPDATE OR DELETE ON risk_evaluation_records
        FOR EACH ROW EXECUTE FUNCTION block_risk_record_mutation();

        DROP TRIGGER IF EXISTS enforce_cov_forecast_immutability ON covariance_forecasts;
        CREATE TRIGGER enforce_cov_forecast_immutability
        BEFORE UPDATE OR DELETE ON covariance_forecasts
        FOR EACH ROW EXECUTE FUNCTION block_risk_record_mutation();

        DROP TRIGGER IF EXISTS enforce_stress_eval_immutability ON stress_evaluation_records;
        CREATE TRIGGER enforce_stress_eval_immutability
        BEFORE UPDATE OR DELETE ON stress_evaluation_records
        FOR EACH ROW EXECUTE FUNCTION block_risk_record_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_stress_eval_immutability ON stress_evaluation_records;
        DROP TRIGGER IF EXISTS enforce_cov_forecast_immutability ON covariance_forecasts;
        DROP TRIGGER IF EXISTS enforce_risk_eval_immutability ON risk_evaluation_records;
        DROP FUNCTION IF EXISTS block_risk_record_mutation();

        DROP TRIGGER IF EXISTS enforce_unique_portfolio_snapshot_id ON risk_evaluation_records;
        DROP FUNCTION IF EXISTS check_unique_portfolio_snapshot_id();

        DROP TABLE IF EXISTS stress_evaluation_records CASCADE;
        DROP TABLE IF EXISTS covariance_forecasts CASCADE;
        DROP TABLE IF EXISTS risk_evaluation_records_default CASCADE;
        DROP TABLE IF EXISTS risk_evaluation_records CASCADE;
    """)
