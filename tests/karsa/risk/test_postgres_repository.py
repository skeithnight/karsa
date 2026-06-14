import pytest
from datetime import datetime
from testcontainers.postgres import PostgresContainer
from psycopg_pool import ConnectionPool
import psycopg
import json

from karsa.risk.exceptions import ImmutabilityViolationException
from karsa.risk.value_objects import (
    AssetExposure,
    ValueAtRisk,
    ExpectedShortfall,
    ConcentrationRisk,
    LiquidityRisk,
    StressScenarioResult,
)
from karsa.risk.models import RiskEvaluationRecord, CovarianceForecast, StressEvaluationRecord
from karsa.risk.repositories import (
    PostgresRiskEvaluationRepository,
    PostgresCovarianceForecastRepository,
    PostgresStressEvaluationRepository,
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
            # Drop tables in correct order
            cur.execute("DROP TABLE IF EXISTS stress_evaluation_records CASCADE;")
            cur.execute("DROP TABLE IF EXISTS covariance_forecasts CASCADE;")
            cur.execute("DROP TABLE IF EXISTS risk_evaluation_records_default CASCADE;")
            cur.execute("DROP TABLE IF EXISTS risk_evaluation_records CASCADE;")

            # 1. Create tables and partitions
            cur.execute("""
                CREATE TABLE risk_evaluation_records (
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

                CREATE TABLE risk_evaluation_records_default PARTITION OF risk_evaluation_records DEFAULT;

                CREATE TABLE covariance_forecasts (
                    forecast_id VARCHAR(128) PRIMARY KEY,
                    matrix_urn VARCHAR(256) NOT NULL UNIQUE,
                    universe_size INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );

                CREATE TABLE stress_evaluation_records (
                    stress_evaluation_id VARCHAR(128) PRIMARY KEY,
                    portfolio_snapshot_id VARCHAR(128) NOT NULL,
                    scenario_urn VARCHAR(256) NOT NULL,
                    shock_results JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
            """)

            # 2. Add global uniqueness trigger for 1:1 cardinality check on portfolio_snapshot_id
            cur.execute("""
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

                CREATE TRIGGER enforce_unique_portfolio_snapshot_id
                BEFORE INSERT ON risk_evaluation_records
                FOR EACH ROW EXECUTE FUNCTION check_unique_portfolio_snapshot_id();
            """)

            # 3. Add immutability triggers to block UPDATE/DELETE on risk tables
            cur.execute("""
                CREATE OR REPLACE FUNCTION block_risk_record_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'Risk records are strictly immutable. UPDATE and DELETE operations are prohibited.';
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER enforce_risk_eval_immutability
                BEFORE UPDATE OR DELETE ON risk_evaluation_records
                FOR EACH ROW EXECUTE FUNCTION block_risk_record_mutation();

                CREATE TRIGGER enforce_cov_forecast_immutability
                BEFORE UPDATE OR DELETE ON covariance_forecasts
                FOR EACH ROW EXECUTE FUNCTION block_risk_record_mutation();

                CREATE TRIGGER enforce_stress_eval_immutability
                BEFORE UPDATE OR DELETE ON stress_evaluation_records
                FOR EACH ROW EXECUTE FUNCTION block_risk_record_mutation();
            """)
        conn.commit()
    return postgres_pool

def test_postgres_save_and_retrieve_evaluation(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresRiskEvaluationRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)

        record = RiskEvaluationRecord(
            evaluation_id="eval-pg-1",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:pg1",
            model_id="parametric-normal",
            model_version="1.0",
            methodology_version="parametric",
            covariance_version="fc-1",
            stress_scenario_version="scenario-v1",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[ValueAtRisk(0.95, 1, 0.05)],
            expected_shortfalls=[ExpectedShortfall(0.95, 1, 0.07)],
            exposures=[AssetExposure("urn:karsa:asset:1", 1.0, 100000.0, "Tech")],
            concentration_risk=ConcentrationRisk(1.0, 0.0, 1.0),
            liquidity_risks=[LiquidityRisk("urn:karsa:asset:1", 0.5, 0.10)],
            created_at=now
        )

        repo.save_evaluation(record)
        conn.commit()

        # Retrieve and assert
        retrieved = repo.get_evaluation_by_id("eval-pg-1")
        assert retrieved is not None
        assert retrieved.evaluation_id == "eval-pg-1"
        assert retrieved.portfolio_snapshot_id == "urn:karsa:portfolio:snapshot:pg1"
        assert retrieved.risk_metrics[0].value == 0.05
        assert retrieved.concentration_risk.hhi == 1.0
        assert retrieved.created_at == now

        # Retrieve by snapshot URN
        retrieved_by_snap = repo.get_evaluation_by_snapshot_id("urn:karsa:portfolio:snapshot:pg1")
        assert retrieved_by_snap is not None
        assert retrieved_by_snap.evaluation_id == "eval-pg-1"

def test_postgres_1to1_snapshot_trigger(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresRiskEvaluationRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)

        record1 = RiskEvaluationRecord(
            evaluation_id="eval-pg-a",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:dup",
            model_id="model", model_version="1.0", methodology_version="p", covariance_version="c", stress_scenario_version="s",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[], expected_shortfalls=[], exposures=[],
            concentration_risk=ConcentrationRisk(1.0, 0.0, 1.0), liquidity_risks=[], created_at=now
        )
        record2 = RiskEvaluationRecord(
            evaluation_id="eval-pg-b",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:dup",  # same snapshot id
            model_id="model", model_version="1.0", methodology_version="p", covariance_version="c", stress_scenario_version="s",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[], expected_shortfalls=[], exposures=[],
            concentration_risk=ConcentrationRisk(1.0, 0.0, 1.0), liquidity_risks=[], created_at=now
        )

        repo.save_evaluation(record1)
        conn.commit()

        with pytest.raises(ImmutabilityViolationException) as exc:
            repo.save_evaluation(record2)
        assert "1:1 cardinality constraint violated" in str(exc.value)

def test_postgres_trigger_blocks_mutations(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresRiskEvaluationRepository(conn)
        cov_repo = PostgresCovarianceForecastRepository(conn)
        stress_repo = PostgresStressEvaluationRepository(conn)
        now = datetime.utcnow().replace(microsecond=0)

        record = RiskEvaluationRecord(
            evaluation_id="eval-mut",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:mut",
            model_id="model", model_version="1.0", methodology_version="p", covariance_version="c", stress_scenario_version="s",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[], expected_shortfalls=[], exposures=[],
            concentration_risk=ConcentrationRisk(1.0, 0.0, 1.0), liquidity_risks=[], created_at=now
        )
        repo.save_evaluation(record)

        forecast = CovarianceForecast("fc-pg", "urn:karsa:risk:covariance:pg", 1, now)
        cov_repo.save_forecast(forecast)

        stress = StressEvaluationRecord(
            "stress-pg", "urn:karsa:portfolio:snapshot:mut", "urn:karsa:risk:scenario:pg",
            StressScenarioResult("urn:karsa:risk:scenario:pg", 0.0, {}), now
        )
        stress_repo.save_stress_evaluation(stress)
        
        conn.commit()

        # Try updates
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException) as exc:
                cur.execute("UPDATE risk_evaluation_records SET model_id = 'new-model' WHERE evaluation_id = 'eval-mut'")
            assert "UPDATE and DELETE operations are prohibited" in str(exc.value)
            conn.rollback()

            with pytest.raises(psycopg.errors.RaiseException) as exc:
                cur.execute("UPDATE covariance_forecasts SET universe_size = 5 WHERE forecast_id = 'fc-pg'")
            assert "UPDATE and DELETE operations are prohibited" in str(exc.value)
            conn.rollback()

            with pytest.raises(psycopg.errors.RaiseException) as exc:
                cur.execute("UPDATE stress_evaluation_records SET scenario_urn = 'new-scenario' WHERE stress_evaluation_id = 'stress-pg'")
            assert "UPDATE and DELETE operations are prohibited" in str(exc.value)
            conn.rollback()

def test_postgres_non_existent_and_unique_violations(clean_db):
    with clean_db.connection() as conn:
        repo = PostgresRiskEvaluationRepository(conn)
        cov_repo = PostgresCovarianceForecastRepository(conn)
        stress_repo = PostgresStressEvaluationRepository(conn)

        # 1. Test GET non-existent
        assert repo.get_evaluation_by_id("non-existent") is None
        assert repo.get_evaluation_by_snapshot_id("non-existent-snapshot") is None
        assert cov_repo.get_forecast_by_id("non-existent") is None
        assert cov_repo.get_latest_forecast() is None
        assert stress_repo.get_stress_evaluation_by_id("non-existent") is None

        # 2. Test UniqueViolation exceptions
        now = datetime.utcnow().replace(microsecond=0)
        record1 = RiskEvaluationRecord(
            evaluation_id="eval-dup",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:dup1",
            model_id="model", model_version="1.0", methodology_version="p", covariance_version="c", stress_scenario_version="s",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[], expected_shortfalls=[], exposures=[],
            concentration_risk=ConcentrationRisk(1.0, 0.0, 1.0), liquidity_risks=[], created_at=now
        )
        repo.save_evaluation(record1)
        conn.commit()

        # Duplicate ID should trigger UniqueViolation
        record2 = RiskEvaluationRecord(
            evaluation_id="eval-dup",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:dup2",
            model_id="model", model_version="1.0", methodology_version="p", covariance_version="c", stress_scenario_version="s",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[], expected_shortfalls=[], exposures=[],
            concentration_risk=ConcentrationRisk(1.0, 0.0, 1.0), liquidity_risks=[], created_at=now
        )
        with pytest.raises(ImmutabilityViolationException):
            repo.save_evaluation(record2)
        conn.rollback()

        # Duplicate Covariance Forecast ID
        forecast1 = CovarianceForecast("fc-dup", "urn:karsa:risk:covariance:dup1", 1, now)
        cov_repo.save_forecast(forecast1)
        conn.commit()

        forecast2 = CovarianceForecast("fc-dup", "urn:karsa:risk:covariance:dup2", 1, now)
        with pytest.raises(ImmutabilityViolationException):
            cov_repo.save_forecast(forecast2)
        conn.rollback()

        # Duplicate Stress Evaluation ID
        stress1 = StressEvaluationRecord(
            "stress-dup", "urn:karsa:portfolio:snapshot:dup1", "urn:karsa:risk:scenario:dup",
            StressScenarioResult("urn:karsa:risk:scenario:dup", 0.0, {}), now
        )
        stress_repo.save_stress_evaluation(stress1)
        conn.commit()

        stress2 = StressEvaluationRecord(
            "stress-dup", "urn:karsa:portfolio:snapshot:dup2", "urn:karsa:risk:scenario:dup",
            StressScenarioResult("urn:karsa:risk:scenario:dup", 0.0, {}), now
        )
        with pytest.raises(ImmutabilityViolationException):
            stress_repo.save_stress_evaluation(stress2)
        conn.rollback()
