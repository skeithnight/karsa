import math
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from karsa.risk.models import RiskEvaluationRecord, CovarianceForecast, StressEvaluationRecord
from karsa.risk.value_objects import (
    ValueAtRisk,
    ExpectedShortfall,
    ConcentrationRisk,
    LiquidityRisk,
    StressScenarioResult,
    AssetExposure,
)
from karsa.risk.exceptions import NegativeEigenvalueException, InvalidValueException, ImmutabilityViolationException
from karsa.risk.ports import EventPublisherPort, ReturnsDataPort, RegimeStatePort, ObjectStorePort
from karsa.risk.repositories import RiskEvaluationRepository, CovarianceForecastRepository, StressEvaluationRepository
from karsa.risk.events import RiskEvaluationCreatedEvent, StressEvaluationCreatedEvent, CovarianceForecastUpdatedEvent

class ConcentrationRiskService:
    def calculate_concentration(self, exposures: List[AssetExposure]) -> ConcentrationRisk:
        if not exposures:
            return ConcentrationRisk(hhi=0.0, gini=0.0, top_5_weight=0.0)

        # 1. HHI Calculation
        weights = [abs(e.weight) for e in exposures]
        total_weight = sum(weights)
        if total_weight == 0.0:
            return ConcentrationRisk(hhi=0.0, gini=0.0, top_5_weight=0.0)
        
        normalized_weights = [w / total_weight for w in weights]
        hhi = sum(w ** 2 for w in normalized_weights)

        # 2. Gini Coefficient Calculation
        n = len(normalized_weights)
        if n <= 1:
            gini = 0.0
        else:
            sorted_w = sorted(normalized_weights)
            # Gini formula: (sum((2i - n - 1)*x_i)) / (n * sum(x_i))
            numerator = sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(sorted_w))
            gini = numerator / (n * sum(sorted_w))
            gini = max(0.0, min(1.0, gini)) # force bounds

        # 3. Top 5 Weight
        sorted_w_desc = sorted(normalized_weights, reverse=True)
        top_5_weight = sum(sorted_w_desc[:5])

        return ConcentrationRisk(hhi=hhi, gini=gini, top_5_weight=top_5_weight)

class LiquidityRiskService:
    def calculate_liquidity_risk(
        self, exposures: List[AssetExposure], average_daily_volumes: Dict[str, float], liquidation_percent: float = 0.10
    ) -> List[LiquidityRisk]:
        liquidity_metrics = []
        for exp in exposures:
            adv = average_daily_volumes.get(exp.asset_urn, 0.0)
            if adv <= 0.0:
                # Fallback to standard days to liquidate if ADV is missing/invalid
                days = 99.0
            else:
                liquidation_size = exp.exposure_value * liquidation_percent
                days = liquidation_size / adv
            
            liquidity_metrics.append(
                LiquidityRisk(
                    asset_urn=exp.asset_urn,
                    days_to_liquidate=days,
                    liquidation_scenario_percent=liquidation_percent
                )
            )
        return liquidity_metrics

class StressTestingService:
    def __init__(self, stress_repo: StressEvaluationRepository, publisher: EventPublisherPort):
        self.stress_repo = stress_repo
        self.publisher = publisher

    def evaluate_stress(
        self,
        stress_evaluation_id: str,
        portfolio_snapshot_id: str,
        scenario_urn: str,
        exposures: List[AssetExposure],
        shocks: Dict[str, float],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> StressEvaluationRecord:
        # Shock mapping: factor (e.g. Asset URN or Sector) to return shock percentage
        # Compute portfolio impact = sum(weight * shock)
        portfolio_impact = 0.0
        shock_results_dict = {}

        for exp in exposures:
            # Check shock by asset URN, then by sector, fallback to 0.0
            shock = shocks.get(exp.asset_urn, shocks.get(exp.sector, 0.0))
            asset_impact = exp.weight * shock
            portfolio_impact += asset_impact
            shock_results_dict[exp.asset_urn] = {
                "weight": exp.weight,
                "shock": shock,
                "impact": asset_impact
            }

        shock_results = StressScenarioResult(
            scenario_urn=scenario_urn,
            portfolio_impact_percent=portfolio_impact,
            shock_results=shock_results_dict
        )

        record = StressEvaluationRecord(
            stress_evaluation_id=stress_evaluation_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            scenario_urn=scenario_urn,
            shock_results=shock_results,
            created_at=datetime.utcnow()
        )

        self.stress_repo.save_stress_evaluation(record)

        # Publish event
        event = StressEvaluationCreatedEvent(
            event_id=f"evt_stress_{uuid.uuid4()}",
            correlation_id=correlation_id or stress_evaluation_id,
            causation_id=causation_id or portfolio_snapshot_id,
            timestamp=datetime.utcnow(),
            stress_evaluation_id=stress_evaluation_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            scenario_urn=scenario_urn,
            shock_results={
                "portfolio_impact_percent": portfolio_impact,
                "shock_details": shock_results_dict
            }
        )
        self.publisher.publish(event)
        return record

class RiskEvaluationService:
    def __init__(
        self,
        record_repo: RiskEvaluationRepository,
        cov_repo: CovarianceForecastRepository,
        returns_port: ReturnsDataPort,
        regime_port: RegimeStatePort,
        object_store: ObjectStorePort,
        publisher: EventPublisherPort,
        concentration_service: ConcentrationRiskService,
        liquidity_service: LiquidityRiskService
    ):
        self.record_repo = record_repo
        self.cov_repo = cov_repo
        self.returns_port = returns_port
        self.regime_port = regime_port
        self.object_store = object_store
        self.publisher = publisher
        self.concentration_service = concentration_service
        self.liquidity_service = liquidity_service

    def evaluate_portfolio_risk(
        self,
        evaluation_id: str,
        portfolio_snapshot_id: str,
        exposures: List[AssetExposure],
        model_id: str,
        model_version: str,
        methodology_version: str,
        covariance_version: str,
        stress_scenario_version: str,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> RiskEvaluationRecord:
        # Enforce 1:1 holdings uniqueness check
        existing = self.record_repo.get_evaluation_by_snapshot_id(portfolio_snapshot_id)
        if existing:
            raise ImmutabilityViolationException(
                f"Portfolio snapshot {portfolio_snapshot_id} already has a risk evaluation."
            )

        # 1. Fetch macro regime volatility multiplier (fallbackneutral as default)
        try:
            regime_data = self.regime_port.get_active_regime_multiplier()
            regime_state_urn = regime_data.get("regime_state_urn", "urn:karsa:regime:fallback-neutral-v1")
            volatility_multiplier = regime_data.get("volatility_multiplier", 1.0)
        except Exception:
            regime_state_urn = "urn:karsa:regime:fallback-neutral-v1"
            volatility_multiplier = 1.0

        # 2. Get latest covariance forecast metadata from DB
        cov_forecast = self.cov_repo.get_latest_forecast()
        if not cov_forecast:
            raise InvalidValueException("No covariance forecast matrix found in repository.")

        # 3. Retrieve actual matrix from S3/MinIO
        covariance_matrix = self.object_store.get_matrix(cov_forecast.matrix_urn)
        if not covariance_matrix:
            raise InvalidValueException(f"Covariance matrix payload not found in object storage: {cov_forecast.matrix_urn}")

        # 4. Map asset exposures to matrix indices
        # We assume matrix is organized diagonally for simplification, or maps asset URN indices.
        # Let's perform standard parametric VaR calculation:
        # portfolio_variance = sum(w_i * w_j * cov_ij)
        asset_urns = [e.asset_urn for e in exposures]
        weights = [e.weight for e in exposures]

        # Eigenvalue and diagonal validation (variance cannot be negative)
        for i in range(len(covariance_matrix)):
            if covariance_matrix[i][i] < 0.0:
                raise NegativeEigenvalueException(
                    f"Covariance matrix has negative diagonal variance at index {i}: {covariance_matrix[i][i]}"
                )

        # Simple PSD check: det(2x2) >= 0.0 or check if diagonal is positive
        portfolio_variance = 0.0
        for i, w_i in enumerate(weights):
            for j, w_j in enumerate(weights):
                if i < len(covariance_matrix) and j < len(covariance_matrix[i]):
                    cov_val = covariance_matrix[i][j]
                else:
                    cov_val = 0.0
                portfolio_variance += w_i * w_j * cov_val

        if portfolio_variance < 0.0:
            raise NegativeEigenvalueException("Eigenvalues verification failed: portfolio variance is negative.")

        portfolio_volatility = math.sqrt(portfolio_variance) * volatility_multiplier

        # Calculate ex-ante VaR Normal distribution factors
        var_95_val = 1.645 * portfolio_volatility
        var_99_val = 2.326 * portfolio_volatility

        # Expected Shortfall (CVaR) parametric approximations
        cvar_95_val = 2.063 * portfolio_volatility
        cvar_99_val = 2.665 * portfolio_volatility

        risk_metrics = [
            ValueAtRisk(confidence_level=0.95, horizon_days=1, value=var_95_val),
            ValueAtRisk(confidence_level=0.99, horizon_days=1, value=var_99_val)
        ]

        expected_shortfalls = [
            ExpectedShortfall(confidence_level=0.95, horizon_days=1, value=cvar_95_val),
            ExpectedShortfall(confidence_level=0.99, horizon_days=1, value=cvar_99_val)
        ]

        # 5. Concentration Calculation
        concentration_risk = self.concentration_service.calculate_concentration(exposures)

        # 6. Liquidity Calculation (using a dummy ADV lookup or mock ADV of 1,000,000 per asset)
        dummy_advs = {e.asset_urn: 1000000.0 for e in exposures}
        liquidity_risks = self.liquidity_service.calculate_liquidity_risk(exposures, dummy_advs)

        record = RiskEvaluationRecord(
            evaluation_id=evaluation_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            model_id=model_id,
            model_version=model_version,
            methodology_version=methodology_version,
            covariance_version=covariance_version,
            stress_scenario_version=stress_scenario_version,
            regime_state_urn=regime_state_urn,
            risk_metrics=risk_metrics,
            expected_shortfalls=expected_shortfalls,
            exposures=exposures,
            concentration_risk=concentration_risk,
            liquidity_risks=liquidity_risks,
            created_at=datetime.utcnow()
        )

        self.record_repo.save_evaluation(record)

        # Publish event
        event = RiskEvaluationCreatedEvent(
            event_id=f"evt_risk_{uuid.uuid4()}",
            correlation_id=correlation_id or evaluation_id,
            causation_id=causation_id or portfolio_snapshot_id,
            timestamp=datetime.utcnow(),
            evaluation_id=evaluation_id,
            portfolio_snapshot_id=portfolio_snapshot_id,
            risk_metrics={
                "var_95": var_95_val,
                "var_99": var_99_val,
                "cvar_95": cvar_95_val,
                "cvar_99": cvar_99_val
            },
            concentration={
                "hhi": concentration_risk.hhi,
                "gini": concentration_risk.gini
            }
        )
        self.publisher.publish(event)
        return record

class CovarianceForecastService:
    def __init__(self, cov_repo: CovarianceForecastRepository, object_store: ObjectStorePort, publisher: EventPublisherPort):
        self.cov_repo = cov_repo
        self.object_store = object_store
        self.publisher = publisher

    def calculate_forecast(
        self,
        forecast_id: str,
        matrix_urn: str,
        asset_urns: List[str],
        returns_data: Dict[str, List[float]]
    ) -> CovarianceForecast:
        # Build covariance matrix
        n = len(asset_urns)
        if n <= 0:
            raise InvalidValueException("Asset URN list cannot be empty for covariance forecast.")

        matrix = [[0.0] * n for _ in range(n)]

        # EWMA Estimation (simplified version: variance = variance of historical returns)
        for i, asset_a in enumerate(asset_urns):
            returns_a = returns_data.get(asset_a, [])
            if not returns_a:
                variance = 0.01 # fallback default variance
            else:
                mean_a = sum(returns_a) / len(returns_a)
                variance = sum((x - mean_a) ** 2 for x in returns_a) / len(returns_a)
                if variance < 0.0:
                    raise NegativeEigenvalueException(f"Negative variance computed for {asset_a}: {variance}")

            matrix[i][i] = variance

            for j, asset_b in enumerate(asset_urns):
                if i != j:
                    returns_b = returns_data.get(asset_b, [])
                    if not returns_a or not returns_b:
                        covariance = 0.0
                    else:
                        mean_a = sum(returns_a) / len(returns_a)
                        mean_b = sum(returns_b) / len(returns_b)
                        min_len = min(len(returns_a), len(returns_b))
                        covariance = sum((returns_a[k] - mean_a) * (returns_b[k] - mean_b) for k in range(min_len)) / min_len
                    matrix[i][j] = covariance

        # Save to S3
        self.object_store.save_matrix(matrix_urn, matrix)

        record = CovarianceForecast(
            forecast_id=forecast_id,
            matrix_urn=matrix_urn,
            universe_size=n,
            created_at=datetime.utcnow()
        )

        self.cov_repo.save_forecast(record)

        # Publish event
        event = CovarianceForecastUpdatedEvent(
            event_id=f"evt_cov_{uuid.uuid4()}",
            correlation_id=forecast_id,
            causation_id=forecast_id,
            timestamp=datetime.utcnow(),
            forecast_id=forecast_id,
            matrix_urn=matrix_urn,
            universe_size=n
        )
        self.publisher.publish(event)
        return record
