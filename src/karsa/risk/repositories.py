from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import json
import psycopg
import copy

from karsa.risk.models import RiskEvaluationRecord, CovarianceForecast, StressEvaluationRecord
from karsa.risk.value_objects import (
    ValueAtRisk,
    ExpectedShortfall,
    ConcentrationRisk,
    LiquidityRisk,
    StressScenarioResult,
    AssetExposure,
)
from karsa.risk.exceptions import ImmutabilityViolationException

class RiskEvaluationRepository(ABC):
    @abstractmethod
    def save_evaluation(self, record: RiskEvaluationRecord) -> None:
        """Saves a risk evaluation record. Raises ImmutabilityViolationException on duplicate."""
        pass

    @abstractmethod
    def get_evaluation_by_id(self, evaluation_id: str) -> Optional[RiskEvaluationRecord]:
        """Retrieves a risk evaluation record by its ID."""
        pass

    @abstractmethod
    def get_evaluation_by_snapshot_id(self, snapshot_id: str) -> Optional[RiskEvaluationRecord]:
        """Retrieves a risk evaluation record by its portfolio snapshot ID URN."""
        pass

class CovarianceForecastRepository(ABC):
    @abstractmethod
    def save_forecast(self, record: CovarianceForecast) -> None:
        """Saves a covariance forecast parameter record."""
        pass

    @abstractmethod
    def get_forecast_by_id(self, forecast_id: str) -> Optional[CovarianceForecast]:
        """Retrieves a covariance forecast by its ID."""
        pass

    @abstractmethod
    def get_latest_forecast(self) -> Optional[CovarianceForecast]:
        """Retrieves the latest covariance forecast."""
        pass

class StressEvaluationRepository(ABC):
    @abstractmethod
    def save_stress_evaluation(self, record: StressEvaluationRecord) -> None:
        """Saves a stress evaluation record."""
        pass

    @abstractmethod
    def get_stress_evaluation_by_id(self, stress_evaluation_id: str) -> Optional[StressEvaluationRecord]:
        """Retrieves a stress evaluation record by its ID."""
        pass

class InMemoryRiskEvaluationRepository(RiskEvaluationRepository):
    def __init__(self):
        self._records: Dict[str, RiskEvaluationRecord] = {}

    def save_evaluation(self, record: RiskEvaluationRecord) -> None:
        if record.evaluation_id in self._records:
            raise ImmutabilityViolationException("Cannot overwrite an existing risk evaluation record.")
        
        # Enforce 1:1 snapshot-to-evaluation cardinality
        for existing in self._records.values():
            if existing.portfolio_snapshot_id == record.portfolio_snapshot_id:
                raise ImmutabilityViolationException(
                    f"Portfolio snapshot {record.portfolio_snapshot_id} already has a risk evaluation record."
                )
        self._records[record.evaluation_id] = copy.deepcopy(record)

    def get_evaluation_by_id(self, evaluation_id: str) -> Optional[RiskEvaluationRecord]:
        rec = self._records.get(evaluation_id)
        if not rec:
            return None
        return copy.deepcopy(rec)

    def get_evaluation_by_snapshot_id(self, snapshot_id: str) -> Optional[RiskEvaluationRecord]:
        for rec in self._records.values():
            if rec.portfolio_snapshot_id == snapshot_id:
                return copy.deepcopy(rec)
        return None

class InMemoryCovarianceForecastRepository(CovarianceForecastRepository):
    def __init__(self):
        self._forecasts: Dict[str, CovarianceForecast] = {}

    def save_forecast(self, record: CovarianceForecast) -> None:
        if record.forecast_id in self._forecasts:
            raise ImmutabilityViolationException("Cannot overwrite an existing covariance forecast record.")
        self._forecasts[record.forecast_id] = copy.deepcopy(record)

    def get_forecast_by_id(self, forecast_id: str) -> Optional[CovarianceForecast]:
        rec = self._forecasts.get(forecast_id)
        if not rec:
            return None
        return copy.deepcopy(rec)

    def get_latest_forecast(self) -> Optional[CovarianceForecast]:
        if not self._forecasts:
            return None
        sorted_forecasts = sorted(self._forecasts.values(), key=lambda x: x.created_at, reverse=True)
        return copy.deepcopy(sorted_forecasts[0])

class InMemoryStressEvaluationRepository(StressEvaluationRepository):
    def __init__(self):
        self._records: Dict[str, StressEvaluationRecord] = {}

    def save_stress_evaluation(self, record: StressEvaluationRecord) -> None:
        if record.stress_evaluation_id in self._records:
            raise ImmutabilityViolationException("Cannot overwrite an existing stress evaluation record.")
        self._records[record.stress_evaluation_id] = copy.deepcopy(record)

    def get_stress_evaluation_by_id(self, stress_evaluation_id: str) -> Optional[StressEvaluationRecord]:
        rec = self._records.get(stress_evaluation_id)
        if not rec:
            return None
        return copy.deepcopy(rec)

class PostgresRiskEvaluationRepository(RiskEvaluationRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_evaluation(self, record: RiskEvaluationRecord) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO risk_evaluation_records (
                        evaluation_id, portfolio_snapshot_id, model_id, model_version, methodology_version, 
                        covariance_version, stress_scenario_version, regime_state_urn, risk_metrics, 
                        expected_shortfalls, exposures, concentration_stats, liquidity_metrics, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.evaluation_id,
                        record.portfolio_snapshot_id,
                        record.model_id,
                        record.model_version,
                        record.methodology_version,
                        record.covariance_version,
                        record.stress_scenario_version,
                        record.regime_state_urn,
                        json.dumps([
                            {"confidence_level": m.confidence_level, "horizon_days": m.horizon_days, "value": m.value}
                            for m in record.risk_metrics
                        ]),
                        json.dumps([
                            {"confidence_level": m.confidence_level, "horizon_days": m.horizon_days, "value": m.value}
                            for m in record.expected_shortfalls
                        ]),
                        json.dumps([
                            {"asset_urn": m.asset_urn, "weight": m.weight, "exposure_value": m.exposure_value, "sector": m.sector}
                            for m in record.exposures
                        ]),
                        json.dumps({
                            "hhi": record.concentration_risk.hhi,
                            "gini": record.concentration_risk.gini,
                            "top_5_weight": record.concentration_risk.top_5_weight,
                        }),
                        json.dumps([
                            {"asset_urn": m.asset_urn, "days_to_liquidate": m.days_to_liquidate, "liquidation_scenario_percent": m.liquidation_scenario_percent}
                            for m in record.liquidity_risks
                        ]),
                        record.created_at
                    )
                )
        except psycopg.errors.UniqueViolation as e:
            raise ImmutabilityViolationException("Risk evaluation record or portfolio snapshot evaluation already exists.") from e
        except psycopg.errors.RaiseException as e:
            raise ImmutabilityViolationException(str(e)) from e

    def get_evaluation_by_id(self, evaluation_id: str) -> Optional[RiskEvaluationRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT evaluation_id, portfolio_snapshot_id, model_id, model_version, methodology_version, 
                       covariance_version, stress_scenario_version, regime_state_urn, risk_metrics, 
                       expected_shortfalls, exposures, concentration_stats, liquidity_metrics, created_at
                FROM risk_evaluation_records
                WHERE evaluation_id = %s
                """,
                (evaluation_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def get_evaluation_by_snapshot_id(self, snapshot_id: str) -> Optional[RiskEvaluationRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT evaluation_id, portfolio_snapshot_id, model_id, model_version, methodology_version, 
                       covariance_version, stress_scenario_version, regime_state_urn, risk_metrics, 
                       expected_shortfalls, exposures, concentration_stats, liquidity_metrics, created_at
                FROM risk_evaluation_records
                WHERE portfolio_snapshot_id = %s
                """,
                (snapshot_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def _row_to_record(self, row) -> RiskEvaluationRecord:
        metrics_data = row[8] if isinstance(row[8], list) else json.loads(row[8])
        es_data = row[9] if isinstance(row[9], list) else json.loads(row[9])
        exposures_data = row[10] if isinstance(row[10], list) else json.loads(row[10])
        concentration_data = row[11] if isinstance(row[11], dict) else json.loads(row[11])
        liquidity_data = row[12] if isinstance(row[12], list) else json.loads(row[12])

        metrics = [ValueAtRisk(**m) for m in metrics_data]
        es = [ExpectedShortfall(**m) for m in es_data]
        exposures = [AssetExposure(**m) for m in exposures_data]
        concentration = ConcentrationRisk(**concentration_data)
        liquidity = [LiquidityRisk(**m) for m in liquidity_data]

        return RiskEvaluationRecord(
            evaluation_id=row[0],
            portfolio_snapshot_id=row[1],
            model_id=row[2],
            model_version=row[3],
            methodology_version=row[4],
            covariance_version=row[5],
            stress_scenario_version=row[6],
            regime_state_urn=row[7],
            risk_metrics=metrics,
            expected_shortfalls=es,
            exposures=exposures,
            concentration_risk=concentration,
            liquidity_risks=liquidity,
            created_at=row[13]
        )

class PostgresCovarianceForecastRepository(CovarianceForecastRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_forecast(self, record: CovarianceForecast) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO covariance_forecasts (
                        forecast_id, matrix_urn, universe_size, created_at
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        record.forecast_id,
                        record.matrix_urn,
                        record.universe_size,
                        record.created_at
                    )
                )
        except psycopg.errors.UniqueViolation as e:
            raise ImmutabilityViolationException("Covariance forecast already exists.") from e
        except psycopg.errors.RaiseException as e:
            raise ImmutabilityViolationException(str(e)) from e

    def get_forecast_by_id(self, forecast_id: str) -> Optional[CovarianceForecast]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT forecast_id, matrix_urn, universe_size, created_at
                FROM covariance_forecasts
                WHERE forecast_id = %s
                """,
                (forecast_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return CovarianceForecast(
                forecast_id=row[0],
                matrix_urn=row[1],
                universe_size=row[2],
                created_at=row[3]
            )

    def get_latest_forecast(self) -> Optional[CovarianceForecast]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT forecast_id, matrix_urn, universe_size, created_at
                FROM covariance_forecasts
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            return CovarianceForecast(
                forecast_id=row[0],
                matrix_urn=row[1],
                universe_size=row[2],
                created_at=row[3]
            )

class PostgresStressEvaluationRepository(StressEvaluationRepository):
    def __init__(self, conn):
        self.conn = conn

    def save_stress_evaluation(self, record: StressEvaluationRecord) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stress_evaluation_records (
                        stress_evaluation_id, portfolio_snapshot_id, scenario_urn, shock_results, created_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        record.stress_evaluation_id,
                        record.portfolio_snapshot_id,
                        record.scenario_urn,
                        json.dumps({
                            "scenario_urn": record.shock_results.scenario_urn,
                            "portfolio_impact_percent": record.shock_results.portfolio_impact_percent,
                            "shock_results": record.shock_results.shock_results
                        }),
                        record.created_at
                    )
                )
        except psycopg.errors.UniqueViolation as e:
            raise ImmutabilityViolationException("Stress evaluation record already exists.") from e
        except psycopg.errors.RaiseException as e:
            raise ImmutabilityViolationException(str(e)) from e

    def get_stress_evaluation_by_id(self, stress_evaluation_id: str) -> Optional[StressEvaluationRecord]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT stress_evaluation_id, portfolio_snapshot_id, scenario_urn, shock_results, created_at
                FROM stress_evaluation_records
                WHERE stress_evaluation_id = %s
                """,
                (stress_evaluation_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            
            shock_data = row[3] if isinstance(row[3], dict) else json.loads(row[3])
            shock_res = StressScenarioResult(
                scenario_urn=shock_data["scenario_urn"],
                portfolio_impact_percent=shock_data["portfolio_impact_percent"],
                shock_results=shock_data["shock_results"]
            )
            return StressEvaluationRecord(
                stress_evaluation_id=row[0],
                portfolio_snapshot_id=row[1],
                scenario_urn=row[2],
                shock_results=shock_res,
                created_at=row[4]
            )
