import pytest
from datetime import datetime, timezone
import math
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Dict, Any, List, Optional

from karsa.risk.exceptions import (
    ImmutabilityViolationException,
    NegativeEigenvalueException,
    InvalidSnapshotURNException,
    InvalidValueException,
)
from karsa.risk.value_objects import (
    ValueAtRisk,
    ExpectedShortfall,
    VolatilityForecast,
    CorrelationForecast,
    ConcentrationRisk,
    LiquidityRisk,
    StressScenarioResult,
    RegimeReference,
    AssetExposure,
)
from karsa.risk.models import RiskEvaluationRecord, CovarianceForecast, StressEvaluationRecord
from karsa.risk.ports import EventPublisherPort, ReturnsDataPort, RegimeStatePort, ObjectStorePort
from karsa.risk.repositories import (
    InMemoryRiskEvaluationRepository,
    InMemoryCovarianceForecastRepository,
    InMemoryStressEvaluationRepository,
)
from karsa.risk.services import (
    ConcentrationRiskService,
    LiquidityRiskService,
    StressTestingService,
    RiskEvaluationService,
    CovarianceForecastService,
)
from karsa.risk.api import router
from karsa.risk.events import RiskEvaluationCreatedEvent, CovarianceForecastUpdatedEvent, StressEvaluationCreatedEvent

# ----------------- Mock Port Implementations -----------------

class MockEventPublisher(EventPublisherPort):
    def __init__(self):
        self.published = []

    def publish(self, event: Any) -> None:
        self.published.append(event)

class MockReturnsDataPort(ReturnsDataPort):
    def get_historical_returns(self, asset_urns: List[str], start_date: datetime, end_date: datetime) -> Dict[str, List[float]]:
        # Returns simple returns arrays
        return {asset: [0.01, -0.005, 0.015, -0.01, 0.008] for asset in asset_urns}

class MockRegimeStatePort(RegimeStatePort):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def get_active_regime_multiplier(self) -> Dict[str, Any]:
        if self.should_fail:
            raise RuntimeError("Regime Engine offline")
        return {
            "regime_state_urn": "urn:karsa:regime:high-vol-regime-4",
            "volatility_multiplier": 1.5
        }

class MockObjectStore(ObjectStorePort):
    def __init__(self):
        self.store = {}

    def save_matrix(self, matrix_urn: str, data: List[List[float]]) -> None:
        self.store[matrix_urn] = copy_matrix(data)

    def get_matrix(self, matrix_urn: str) -> List[List[float]]:
        return copy_matrix(self.store.get(matrix_urn))

def copy_matrix(matrix):
    if matrix is None:
        return None
    return [list(row) for row in matrix]

# ----------------- Fixtures -----------------

@pytest.fixture
def service_setup():
    record_repo = InMemoryRiskEvaluationRepository()
    cov_repo = InMemoryCovarianceForecastRepository()
    stress_repo = InMemoryStressEvaluationRepository()
    
    publisher = MockEventPublisher()
    returns_port = MockReturnsDataPort()
    regime_port = MockRegimeStatePort()
    object_store = MockObjectStore()
    
    concentration_service = ConcentrationRiskService()
    liquidity_service = LiquidityRiskService()
    stress_service = StressTestingService(stress_repo, publisher)
    
    risk_service = RiskEvaluationService(
        record_repo=record_repo,
        cov_repo=cov_repo,
        returns_port=returns_port,
        regime_port=regime_port,
        object_store=object_store,
        publisher=publisher,
        concentration_service=concentration_service,
        liquidity_service=liquidity_service
    )
    
    cov_service = CovarianceForecastService(cov_repo, object_store, publisher)
    
    return (
        record_repo, cov_repo, stress_repo, publisher, returns_port, 
        regime_port, object_store, concentration_service, liquidity_service, 
        stress_service, risk_service, cov_service
    )

@pytest.fixture
def api_client(service_setup):
    (
        _, _, _, _, _, _, _, _, _, stress_service, risk_service, cov_service
    ) = service_setup
    
    app = FastAPI()
    app.include_router(router)
    
    from karsa.risk.api import get_risk_evaluation_service, get_stress_testing_service, get_covariance_forecast_service
    app.dependency_overrides[get_risk_evaluation_service] = lambda: risk_service
    app.dependency_overrides[get_stress_testing_service] = lambda: stress_service
    app.dependency_overrides[get_covariance_forecast_service] = lambda: cov_service
    
    return TestClient(app)

# ----------------- Value Object Validation Tests -----------------

def test_value_object_validations():
    # ValueAtRisk validations
    with pytest.raises(InvalidValueException):
        ValueAtRisk(confidence_level=1.2, horizon_days=1, value=0.05)
    with pytest.raises(InvalidValueException):
        ValueAtRisk(confidence_level=0.95, horizon_days=-1, value=0.05)
    with pytest.raises(InvalidValueException):
        ValueAtRisk(confidence_level=0.95, horizon_days=1, value=-0.05)

    # ExpectedShortfall validations
    with pytest.raises(InvalidValueException):
        ExpectedShortfall(confidence_level=-0.1, horizon_days=1, value=0.05)
    
    # VolatilityForecast validations
    with pytest.raises(InvalidValueException):
        VolatilityForecast(asset_urn=" ", annualized_volatility=0.2)
    with pytest.raises(InvalidValueException):
        VolatilityForecast(asset_urn="urn:karsa:asset:1", annualized_volatility=-0.1)

    # CorrelationForecast validations
    with pytest.raises(InvalidValueException):
        CorrelationForecast(asset_urn_a="", asset_urn_b="urn:b", correlation=0.5)
    with pytest.raises(InvalidValueException):
        CorrelationForecast(asset_urn_a="urn:a", asset_urn_b="urn:b", correlation=1.5)

    # ConcentrationRisk validations
    with pytest.raises(InvalidValueException):
        ConcentrationRisk(hhi=1.5, gini=0.5, top_5_weight=0.5)
    with pytest.raises(InvalidValueException):
        ConcentrationRisk(hhi=0.5, gini=-0.5, top_5_weight=0.5)
    with pytest.raises(InvalidValueException):
        ConcentrationRisk(hhi=0.5, gini=0.5, top_5_weight=1.5)

    # LiquidityRisk validations
    with pytest.raises(InvalidValueException):
        LiquidityRisk(asset_urn=" ", days_to_liquidate=5.0, liquidation_scenario_percent=0.10)
    with pytest.raises(InvalidValueException):
        LiquidityRisk(asset_urn="urn:a", days_to_liquidate=-1.0, liquidation_scenario_percent=0.10)
    with pytest.raises(InvalidValueException):
        LiquidityRisk(asset_urn="urn:a", days_to_liquidate=5.0, liquidation_scenario_percent=1.5)

    # StressScenarioResult validations
    with pytest.raises(InvalidValueException):
        StressScenarioResult(scenario_urn="", portfolio_impact_percent=-0.05, shock_results={})

    # RegimeReference validations
    with pytest.raises(InvalidValueException):
        RegimeReference(regime_state_urn="urn:other:regime:1", volatility_multiplier=1.2)
    with pytest.raises(InvalidValueException):
        RegimeReference(regime_state_urn="urn:karsa:regime:1", volatility_multiplier=-0.5)

# ----------------- Aggregate Immutability Tests -----------------

def test_aggregate_immutability():
    # Setup record
    rec = RiskEvaluationRecord(
        evaluation_id="eval-1",
        portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
        model_id="model-a",
        model_version="1.0",
        methodology_version="historical",
        covariance_version="cov-v1",
        stress_scenario_version="scenario-v1",
        regime_state_urn="urn:karsa:regime:neutral",
        risk_metrics=[],
        expected_shortfalls=[],
        exposures=[],
        concentration_risk=ConcentrationRisk(0.1, 0.2, 0.3),
        liquidity_risks=[],
        created_at=datetime.utcnow()
    )

    with pytest.raises(ImmutabilityViolationException):
        rec.model_id = "model-b"

    with pytest.raises(ImmutabilityViolationException):
        del rec.model_id

    # Verify URN checks in constructor
    with pytest.raises(InvalidSnapshotURNException):
        RiskEvaluationRecord(
            evaluation_id="eval-1",
            portfolio_snapshot_id="urn:other:snapshot:1",
            model_id="model-a",
            model_version="1.0",
            methodology_version="historical",
            covariance_version="cov-v1",
            stress_scenario_version="scenario-v1",
            regime_state_urn="urn:karsa:regime:neutral",
            risk_metrics=[],
            expected_shortfalls=[],
            exposures=[],
            concentration_risk=ConcentrationRisk(0.1, 0.2, 0.3),
            liquidity_risks=[],
            created_at=datetime.utcnow()
        )

# ----------------- Service Logic & Calculations -----------------

def test_concentration_calculation(service_setup):
    _, _, _, _, _, _, _, concentration_service, _, _, _, _ = service_setup
    
    exposures = [
        AssetExposure("urn:karsa:asset:1", 0.4, 40000.0, "Tech"),
        AssetExposure("urn:karsa:asset:2", 0.3, 30000.0, "Tech"),
        AssetExposure("urn:karsa:asset:3", 0.2, 20000.0, "Finance"),
        AssetExposure("urn:karsa:asset:4", 0.1, 10000.0, "Consumer"),
    ]

    res = concentration_service.calculate_concentration(exposures)
    
    # Expected HHI = 0.4^2 + 0.3^2 + 0.2^2 + 0.1^2 = 0.16 + 0.09 + 0.04 + 0.01 = 0.30
    assert math.isclose(res.hhi, 0.30, rel_tol=1e-5)
    # Gini coefficient: sorted normalized: 0.1, 0.2, 0.3, 0.4
    # Gini = ((2*1 - 4 - 1)*0.1 + (2*2 - 4 - 1)*0.2 + (2*3 - 4 - 1)*0.3 + (2*4 - 4 - 1)*0.4) / (4 * 1.0)
    #      = (-3*0.1 - 1*0.2 + 1*0.3 + 3*0.4) / 4 = (-0.3 - 0.2 + 0.3 + 1.2) / 4 = 1.0 / 4 = 0.25
    assert math.isclose(res.gini, 0.25, rel_tol=1e-5)
    assert math.isclose(res.top_5_weight, 1.0, rel_tol=1e-5)

    # Empty exposures case
    res_empty = concentration_service.calculate_concentration([])
    assert res_empty.hhi == 0.0
    assert res_empty.gini == 0.0

def test_liquidity_calculation(service_setup):
    _, _, _, _, _, _, _, _, liquidity_service, _, _, _ = service_setup

    exposures = [
        AssetExposure("urn:karsa:asset:1", 0.5, 50000.0, "Tech"),
        AssetExposure("urn:karsa:asset:2", 0.5, 50000.0, "Finance"),
    ]

    advs = {
        "urn:karsa:asset:1": 10000.0, # ADV
        "urn:karsa:asset:2": 0.0,      # ADV missing/invalid
    }

    res = liquidity_service.calculate_liquidity_risk(exposures, advs, liquidation_percent=0.10)
    
    # For asset 1: size = 50000 * 0.10 = 5000. ADV = 10000. DTL = 0.5
    assert res[0].asset_urn == "urn:karsa:asset:1"
    assert math.isclose(res[0].days_to_liquidate, 0.5, rel_tol=1e-5)

    # For asset 2: ADV is 0, fallback DTL = 99.0
    assert res[1].asset_urn == "urn:karsa:asset:2"
    assert res[1].days_to_liquidate == 99.0

def test_stress_testing_evaluation(service_setup):
    _, _, stress_repo, publisher, _, _, _, _, _, stress_service, _, _ = service_setup

    exposures = [
        AssetExposure("urn:karsa:asset:1", 0.6, 60000.0, "Tech"),
        AssetExposure("urn:karsa:asset:2", 0.4, 40000.0, "Finance"),
    ]

    shocks = {
        "urn:karsa:asset:1": -0.10, # Tech shocks down 10%
        "Finance": 0.05,            # Finance sector up 5%
    }

    record = stress_service.evaluate_stress(
        stress_evaluation_id="stress-1",
        portfolio_snapshot_id="urn:karsa:portfolio:snapshot:100",
        scenario_urn="urn:karsa:risk:scenario:tech-meltdown",
        exposures=exposures,
        shocks=shocks
    )

    # Expected impact = 0.6 * (-0.10) + 0.4 * 0.05 = -0.06 + 0.02 = -0.04
    assert math.isclose(record.shock_results.portfolio_impact_percent, -0.04, rel_tol=1e-5)
    
    # Verify repo save
    saved = stress_repo.get_stress_evaluation_by_id("stress-1")
    assert saved is not None
    assert saved.scenario_urn == "urn:karsa:risk:scenario:tech-meltdown"

    # Verify event published
    assert len(publisher.published) == 1
    assert isinstance(publisher.published[0], StressEvaluationCreatedEvent)
    assert publisher.published[0].stress_evaluation_id == "stress-1"

def test_covariance_forecast_and_eigenvalues(service_setup):
    _, cov_repo, _, publisher, returns_port, _, object_store, _, _, _, _, cov_service = service_setup

    asset_urns = ["urn:karsa:asset:1", "urn:karsa:asset:2"]
    returns_data = returns_port.get_historical_returns(asset_urns, datetime.utcnow(), datetime.utcnow())

    forecast = cov_service.calculate_forecast(
        forecast_id="fc-1",
        matrix_urn="urn:karsa:risk:covariance:20260614",
        asset_urns=asset_urns,
        returns_data=returns_data
    )

    assert forecast.forecast_id == "fc-1"
    assert forecast.universe_size == 2
    
    # Verify object store has matrix
    stored_matrix = object_store.get_matrix("urn:karsa:risk:covariance:20260614")
    assert stored_matrix is not None
    assert len(stored_matrix) == 2
    assert stored_matrix[0][0] > 0.0 # variance is positive

    # Verify event published
    assert len(publisher.published) == 1
    assert isinstance(publisher.published[0], CovarianceForecastUpdatedEvent)

def test_risk_evaluation_parametric(service_setup):
    (
        record_repo, cov_repo, _, publisher, _, _, object_store, _, _, _, risk_service, cov_service
    ) = service_setup

    # 1. Setup covariance forecast
    # Diagonal variances: 0.04 (vol=0.2), 0.01 (vol=0.1)
    matrix = [[0.04, 0.0], [0.0, 0.01]]
    object_store.save_matrix("urn:karsa:risk:covariance:test", matrix)
    cov_repo.save_forecast(
        CovarianceForecast("fc-1", "urn:karsa:risk:covariance:test", 2, datetime.utcnow())
    )

    exposures = [
        AssetExposure("urn:karsa:asset:1", 0.5, 50000.0, "Tech"),
        AssetExposure("urn:karsa:asset:2", 0.5, 50000.0, "Finance"),
    ]

    record = risk_service.evaluate_portfolio_risk(
        evaluation_id="eval-1",
        portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
        exposures=exposures,
        model_id="parametric-normal",
        model_version="1.0",
        methodology_version="parametric",
        covariance_version="fc-1",
        stress_scenario_version="scenario-v1"
    )

    assert record.evaluation_id == "eval-1"
    # Volatility calculations:
    # variance = 0.5^2 * 0.04 + 0.5^2 * 0.01 = 0.25 * 0.04 + 0.25 * 0.01 = 0.01 + 0.0025 = 0.0125
    # volatility = sqrt(0.0125) = 0.1118
    # Adjusted by regime volatility_multiplier (Mock is 1.5) = 0.1118 * 1.5 = 0.1677
    # VaR 95% = 1.645 * 0.1677 = 0.2758
    assert math.isclose(record.risk_metrics[0].value, 1.645 * math.sqrt(0.0125) * 1.5, rel_tol=1e-4)
    assert record.model_id == "parametric-normal"
    assert record.regime_state_urn == "urn:karsa:regime:high-vol-regime-4"

    # Verify duplicate evaluation raises ImmutabilityViolationException (1:1 constraint)
    with pytest.raises(ImmutabilityViolationException):
        risk_service.evaluate_portfolio_risk(
            evaluation_id="eval-2",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1", # same snapshot
            exposures=exposures,
            model_id="parametric-normal",
            model_version="1.0",
            methodology_version="parametric",
            covariance_version="fc-1",
            stress_scenario_version="scenario-v1"
        )

def test_fallback_regime_behavior(service_setup):
    (
        record_repo, cov_repo, _, _, _, regime_port, object_store, _, _, _, risk_service, _
    ) = service_setup

    # Force regime lookup to fail
    regime_port.should_fail = True

    matrix = [[0.01]]
    object_store.save_matrix("urn:karsa:risk:covariance:fallback", matrix)
    cov_repo.save_forecast(
        CovarianceForecast("fc-fallback", "urn:karsa:risk:covariance:fallback", 1, datetime.utcnow())
    )

    exposures = [AssetExposure("urn:karsa:asset:1", 1.0, 100000.0, "Tech")]

    record = risk_service.evaluate_portfolio_risk(
        evaluation_id="eval-fallback",
        portfolio_snapshot_id="urn:karsa:portfolio:snapshot:fallback",
        exposures=exposures,
        model_id="parametric-normal",
        model_version="1.0",
        methodology_version="parametric",
        covariance_version="fc-fallback",
        stress_scenario_version="scenario-v1"
    )

    # Verification: fallback regime state is urn:karsa:regime:fallback-neutral-v1, and multiplier is 1.0
    assert record.regime_state_urn == "urn:karsa:regime:fallback-neutral-v1"
    # Volatility = sqrt(0.01) = 0.1. VaR 95% = 1.645 * 0.1 * 1.0 = 0.1645
    assert math.isclose(record.risk_metrics[0].value, 0.1645, rel_tol=1e-4)

def test_negative_eigenvalue_check(service_setup):
    (
        _, cov_repo, _, _, _, _, object_store, _, _, _, risk_service, _
    ) = service_setup

    # Variance cannot be negative, set to -0.01
    matrix = [[-0.01]]
    object_store.save_matrix("urn:karsa:risk:covariance:negative", matrix)
    cov_repo.save_forecast(
        CovarianceForecast("fc-neg", "urn:karsa:risk:covariance:negative", 1, datetime.utcnow())
    )

    exposures = [AssetExposure("urn:karsa:asset:1", 1.0, 100000.0, "Tech")]

    with pytest.raises(NegativeEigenvalueException):
        risk_service.evaluate_portfolio_risk(
            evaluation_id="eval-neg",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:neg",
            exposures=exposures,
            model_id="parametric-normal",
            model_version="1.0",
            methodology_version="parametric",
            covariance_version="fc-neg",
            stress_scenario_version="scenario-v1"
        )

# ----------------- Replayability Validation -----------------

def test_replayability_verification(service_setup):
    (
        record_repo, cov_repo, _, _, _, _, object_store, _, _, _, risk_service, _
    ) = service_setup

    matrix = [[0.04]]
    object_store.save_matrix("urn:karsa:risk:covariance:replay", matrix)
    cov_repo.save_forecast(
        CovarianceForecast("fc-replay", "urn:karsa:risk:covariance:replay", 1, datetime.utcnow())
    )

    exposures = [AssetExposure("urn:karsa:asset:1", 1.0, 100000.0, "Tech")]

    # First evaluation
    record = risk_service.evaluate_portfolio_risk(
        evaluation_id="eval-replay-1",
        portfolio_snapshot_id="urn:karsa:portfolio:snapshot:replay",
        exposures=exposures,
        model_id="parametric-normal",
        model_version="1.0",
        methodology_version="parametric",
        covariance_version="fc-replay",
        stress_scenario_version="scenario-v1"
    )

    # Replay calculation manually using parameters stored in the record
    # Verify they output identical VaR calculations
    volatility = math.sqrt(matrix[0][0])
    # Regime is high-vol (1.5 multiplier)
    volatility_adjusted = volatility * 1.5
    expected_var_95 = 1.645 * volatility_adjusted
    
    assert math.isclose(record.risk_metrics[0].value, expected_var_95, rel_tol=1e-5)

# ----------------- API Endpoints Tests -----------------

def test_api_endpoints(api_client, service_setup):
    # Setup covariance forecast to prevent errors on API calls
    _, cov_repo, _, _, _, _, object_store, _, _, _, _, _ = service_setup
    matrix = [[0.04]]
    object_store.save_matrix("urn:karsa:risk:covariance:api", matrix)
    cov_repo.save_forecast(
        CovarianceForecast("fc-api", "urn:karsa:risk:covariance:api", 1, datetime.utcnow())
    )

    # 1. Test POST /risk/evaluations
    payload = {
        "evaluation_id": "eval-api",
        "portfolio_snapshot_id": "urn:karsa:portfolio:snapshot:api",
        "exposures": [
            {"asset_urn": "urn:karsa:asset:1", "weight": 1.0, "exposure_value": 100000.0, "sector": "Tech"}
        ],
        "model_id": "parametric-normal",
        "model_version": "1.0",
        "methodology_version": "parametric",
        "covariance_version": "fc-api",
        "stress_scenario_version": "scenario-v1"
    }

    response = api_client.post("/risk/evaluations", json=payload)
    assert response.status_code == 201
    assert response.json()["evaluation_id"] == "eval-api"

    # 2. Test GET /risk/evaluations/{id}
    response_get = api_client.get("/risk/evaluations/eval-api")
    assert response_get.status_code == 200
    assert response_get.json()["regime_state_urn"] == "urn:karsa:regime:high-vol-regime-4"
    assert response_get.json()["concentration_stats"]["hhi"] == 1.0

    # 3. Test POST /risk/stress-tests
    stress_payload = {
        "stress_evaluation_id": "stress-api",
        "portfolio_snapshot_id": "urn:karsa:portfolio:snapshot:api",
        "scenario_urn": "urn:karsa:risk:scenario:market-shock",
        "exposures": [
            {"asset_urn": "urn:karsa:asset:1", "weight": 1.0, "exposure_value": 100000.0, "sector": "Tech"}
        ],
        "shocks": {"Tech": -0.05}
    }
    response_stress = api_client.post("/risk/stress-tests", json=stress_payload)
    assert response_stress.status_code == 201
    assert response_stress.json()["portfolio_impact_percent"] == -0.05

    # 4. Test GET /risk/stress-tests/{id}
    response_stress_get = api_client.get("/risk/stress-tests/stress-api")
    assert response_stress_get.status_code == 200
    assert response_stress_get.json()["scenario_urn"] == "urn:karsa:risk:scenario:market-shock"

    # 5. Test POST /risk/covariance-forecasts
    cov_payload = {
        "forecast_id": "fc-api-2",
        "matrix_urn": "urn:karsa:risk:covariance:api2",
        "asset_urns": ["urn:karsa:asset:1"],
        "returns_data": {"urn:karsa:asset:1": [0.01, -0.02, 0.015]}
    }
    response_cov = api_client.post("/risk/covariance-forecasts", json=cov_payload)
    assert response_cov.status_code == 201

    # 6. Test GET /risk/covariance-forecasts/latest
    response_latest_cov = api_client.get("/risk/covariance-forecasts/latest")
    assert response_latest_cov.status_code == 200
    assert response_latest_cov.json()["forecast_id"] == "fc-api-2"

def test_api_error_responses(api_client):
    # Test GET evaluation not found
    response = api_client.get("/risk/evaluations/not-exist")
    assert response.status_code == 404

    # Test GET stress evaluation not found
    response_stress = api_client.get("/risk/stress-tests/not-exist")
    assert response_stress.status_code == 404

    # Test GET latest covariance forecast not found (when DB is empty)
    # The fixture service_setup has empty DB, so a new client with empty DB will return 404
    empty_app = FastAPI()
    empty_app.include_router(router)
    empty_client = TestClient(empty_app)
    response_latest = empty_client.get("/risk/covariance-forecasts/latest")
    assert response_latest.status_code == 404

def test_unconfigured_api():
    from karsa.risk import api
    # Reset globally configured services
    old_risk = api._risk_evaluation_service
    old_stress = api._stress_testing_service
    old_cov = api._covariance_forecast_service
    try:
        api._risk_evaluation_service = None
        api._stress_testing_service = None
        api._covariance_forecast_service = None
        with pytest.raises(RuntimeError) as exc:
            api.get_risk_evaluation_service()
        assert "RiskEvaluationService not configured for API." in str(exc.value)

        with pytest.raises(RuntimeError) as exc:
            api.get_stress_testing_service()
        assert "StressTestingService not configured for API." in str(exc.value)

        with pytest.raises(RuntimeError) as exc:
            api.get_covariance_forecast_service()
        assert "CovarianceForecastService not configured for API." in str(exc.value)
    finally:
        api._risk_evaluation_service = old_risk
        api._stress_testing_service = old_stress
        api._covariance_forecast_service = old_cov

def test_additional_model_and_value_object_validations():
    from karsa.risk.projections import RiskSummaryProjection

    # 1. Projections validations
    with pytest.raises(InvalidValueException) as exc:
        RiskSummaryProjection("", "urn:karsa:portfolio:snapshot:1", 0.05, 0.08, 0.1, 0.2, datetime.utcnow())
    assert "evaluation_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskSummaryProjection("eval-1", "", 0.05, 0.08, 0.1, 0.2, datetime.utcnow())
    assert "portfolio_snapshot_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskSummaryProjection("eval-1", "urn:karsa:portfolio:snapshot:1", -0.05, 0.08, 0.1, 0.2, datetime.utcnow())
    assert "VaR values must be non-negative" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskSummaryProjection("eval-1", "urn:karsa:portfolio:snapshot:1", 0.05, 0.08, 1.5, 0.2, datetime.utcnow())
    assert "HHI and Gini must be between 0.0 and 1.0" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskSummaryProjection("eval-1", "urn:karsa:portfolio:snapshot:1", 0.05, 0.08, 0.1, 0.2, "not-a-datetime")
    assert "created_at must be a datetime instance" in str(exc.value)

    # 2. Value Objects validations
    with pytest.raises(InvalidValueException) as exc:
        ExpectedShortfall(0.95, -1, 0.05)
    assert "Horizon days must be positive" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        ExpectedShortfall(0.95, 1, -0.05)
    assert "Expected Shortfall must be non-negative" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        CorrelationForecast("urn:a", "", 0.5)
    assert "Asset URN B cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        StressScenarioResult("urn:scenario", 0.05, None)
    assert "Shock results dictionary cannot be None" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RegimeReference("", 1.0)
    assert "Regime state URN cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        AssetExposure("", 0.1, 100.0, "Tech")
    assert "Asset URN cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        AssetExposure("urn:a", 2.0, 100.0, "Tech")
    assert "Weight must be between -1.0 and 1.0" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        AssetExposure("urn:a", 0.1, -10.0, "Tech")
    assert "Exposure value must be non-negative" in str(exc.value)

    # 3. Aggregate validations
    now = datetime.utcnow()
    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "evaluation_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidSnapshotURNException) as exc:
        RiskEvaluationRecord("e", "", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "portfolio_snapshot_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidSnapshotURNException) as exc:
        RiskEvaluationRecord("e", "urn:invalid:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "portfolio_snapshot_id must start with" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "model_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "model_version cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "methodology_version cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "covariance_version cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "stress_scenario_version cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "regime_state_urn cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:invalid:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "regime_state_urn must start with" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", ["not-var"], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "risk_metrics must be a list of ValueAtRisk instances" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], ["not-es"], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "expected_shortfalls must be a list of ExpectedShortfall instances" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], ["not-exp"], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    assert "exposures must be a list of AssetExposure instances" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], "not-concentration", [], now)
    assert "concentration_risk must be a ConcentrationRisk instance" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), ["not-liq"], now)
    assert "liquidity_risks must be a list of LiquidityRisk instances" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], "not-datetime")
    assert "created_at must be a datetime instance" in str(exc.value)

    # CovarianceForecast validations
    with pytest.raises(InvalidValueException) as exc:
        CovarianceForecast("", "urn:karsa:risk:covariance:1", 5, now)
    assert "forecast_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        CovarianceForecast("f", "", 5, now)
    assert "matrix_urn cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        CovarianceForecast("f", "urn:invalid:covariance:1", 5, now)
    assert "matrix_urn must start with" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        CovarianceForecast("f", "urn:karsa:risk:covariance:1", 0, now)
    assert "universe_size must be positive" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        CovarianceForecast("f", "urn:karsa:risk:covariance:1", 5, "not-datetime")
    assert "created_at must be a datetime instance" in str(exc.value)

    # StressEvaluationRecord validations
    with pytest.raises(InvalidValueException) as exc:
        StressEvaluationRecord("", "urn:karsa:portfolio:snapshot:1", "urn:karsa:risk:scenario:1", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), now)
    assert "stress_evaluation_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidSnapshotURNException) as exc:
        StressEvaluationRecord("s", "", "urn:karsa:risk:scenario:1", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), now)
    assert "portfolio_snapshot_id cannot be empty" in str(exc.value)

    with pytest.raises(InvalidSnapshotURNException) as exc:
        StressEvaluationRecord("s", "urn:invalid:snapshot:1", "urn:karsa:risk:scenario:1", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), now)
    assert "portfolio_snapshot_id must start with" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        StressEvaluationRecord("s", "urn:karsa:portfolio:snapshot:1", "", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), now)
    assert "scenario_urn cannot be empty" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        StressEvaluationRecord("s", "urn:karsa:portfolio:snapshot:1", "urn:invalid:scenario:1", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), now)
    assert "scenario_urn must start with" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        StressEvaluationRecord("s", "urn:karsa:portfolio:snapshot:1", "urn:karsa:risk:scenario:1", "not-stress-result", now)
    assert "shock_results must be a StressScenarioResult instance" in str(exc.value)

    with pytest.raises(InvalidValueException) as exc:
        StressEvaluationRecord("s", "urn:karsa:portfolio:snapshot:1", "urn:karsa:risk:scenario:1", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), "not-datetime")
    assert "created_at must be a datetime instance" in str(exc.value)

    # Immutability check via delattr / setattr
    rec = RiskEvaluationRecord("e", "urn:karsa:portfolio:snapshot:1", "m", "v", "mv", "cv", "sv", "urn:karsa:regime:1", [], [], [], ConcentrationRisk(0.1, 0.2, 0.3), [], now)
    with pytest.raises(ImmutabilityViolationException):
        del rec.evaluation_id
    with pytest.raises(ImmutabilityViolationException):
        rec.evaluation_id = "new"
    # test setattr of new attribute
    rec.new_attr = "val"
    assert rec.new_attr == "val"

    # 4. InMemory Repositories duplicate checks
    repo = InMemoryRiskEvaluationRepository()
    repo.save_evaluation(rec)
    with pytest.raises(ImmutabilityViolationException):
        repo.save_evaluation(rec)

    cov_repo = InMemoryCovarianceForecastRepository()
    fc = CovarianceForecast("f", "urn:karsa:risk:covariance:1", 5, now)
    cov_repo.save_forecast(fc)
    with pytest.raises(ImmutabilityViolationException):
        cov_repo.save_forecast(fc)

    stress_repo = InMemoryStressEvaluationRepository()
    se = StressEvaluationRecord("s", "urn:karsa:portfolio:snapshot:1", "urn:karsa:risk:scenario:1", StressScenarioResult("urn:karsa:risk:scenario:1", 0.0, {}), now)
    stress_repo.save_stress_evaluation(se)
    with pytest.raises(ImmutabilityViolationException):
        stress_repo.save_stress_evaluation(se)

def test_api_exceptions(api_client, service_setup):
    from unittest.mock import patch
    (
        _, _, _, _, _, _, _, _, _, stress_service, risk_service, cov_service
    ) = service_setup

    # Mock risk_service.evaluate_portfolio_risk to raise exceptions
    payload = {
        "evaluation_id": "eval-api-err",
        "portfolio_snapshot_id": "urn:karsa:portfolio:snapshot:err",
        "exposures": [],
        "model_id": "m",
        "model_version": "v",
        "methodology_version": "mv",
        "covariance_version": "cv",
        "stress_scenario_version": "sv"
    }

    with patch.object(risk_service, "evaluate_portfolio_risk") as mock_eval:
        # ImmutabilityViolationException -> 409
        mock_eval.side_effect = ImmutabilityViolationException("conflict")
        response = api_client.post("/risk/evaluations", json=payload)
        assert response.status_code == 409

        # NegativeEigenvalueException -> 400
        mock_eval.side_effect = NegativeEigenvalueException("eigenvalue")
        response = api_client.post("/risk/evaluations", json=payload)
        assert response.status_code == 400

        # InvalidSnapshotURNException -> 400
        mock_eval.side_effect = InvalidSnapshotURNException("snapshot URN")
        response = api_client.post("/risk/evaluations", json=payload)
        assert response.status_code == 400

        # InvalidValueException -> 400
        mock_eval.side_effect = InvalidValueException("value invalid")
        response = api_client.post("/risk/evaluations", json=payload)
        assert response.status_code == 400

    # Mock stress_service.evaluate_stress to raise exceptions
    stress_payload = {
        "stress_evaluation_id": "stress-api-err",
        "portfolio_snapshot_id": "urn:karsa:portfolio:snapshot:err",
        "scenario_urn": "urn:karsa:risk:scenario:err",
        "exposures": [],
        "shocks": {}
    }

    with patch.object(stress_service, "evaluate_stress") as mock_stress:
        # ImmutabilityViolationException -> 409
        mock_stress.side_effect = ImmutabilityViolationException("conflict")
        response = api_client.post("/risk/stress-tests", json=stress_payload)
        assert response.status_code == 409

        # InvalidSnapshotURNException -> 400
        mock_stress.side_effect = InvalidSnapshotURNException("snapshot URN")
        response = api_client.post("/risk/stress-tests", json=stress_payload)
        assert response.status_code == 400

        # InvalidValueException -> 400
        mock_stress.side_effect = InvalidValueException("value invalid")
        response = api_client.post("/risk/stress-tests", json=stress_payload)
        assert response.status_code == 400

    # Mock cov_service.calculate_forecast to raise exceptions
    cov_payload = {
        "forecast_id": "fc-api-err",
        "matrix_urn": "urn:karsa:risk:covariance:err",
        "asset_urns": [],
        "returns_data": {}
    }

    with patch.object(cov_service, "calculate_forecast") as mock_cov:
        # ImmutabilityViolationException -> 409
        mock_cov.side_effect = ImmutabilityViolationException("conflict")
        response = api_client.post("/risk/covariance-forecasts", json=cov_payload)
        assert response.status_code == 409

        # NegativeEigenvalueException -> 400
        mock_cov.side_effect = NegativeEigenvalueException("eigenvalue")
        response = api_client.post("/risk/covariance-forecasts", json=cov_payload)
        assert response.status_code == 400

        # InvalidValueException -> 400
        mock_cov.side_effect = InvalidValueException("value invalid")
        response = api_client.post("/risk/covariance-forecasts", json=cov_payload)
        assert response.status_code == 400

def test_service_edge_cases(service_setup):
    (
        record_repo, cov_repo, stress_repo, publisher, returns_port, 
        regime_port, object_store, concentration_service, liquidity_service, 
        stress_service, risk_service, cov_service
    ) = service_setup

    # 1. calculate_concentration with total_weight = 0.0
    exposures_zero = [AssetExposure("urn:karsa:asset:1", 0.0, 0.0, "Tech")]
    res = concentration_service.calculate_concentration(exposures_zero)
    assert res.hhi == 0.0
    assert res.gini == 0.0
    assert res.top_5_weight == 0.0

    # 2. evaluate_portfolio_risk no covariance forecast
    cov_repo._forecasts.clear()
    with pytest.raises(InvalidValueException) as exc:
        risk_service.evaluate_portfolio_risk(
            evaluation_id="eval-1",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
            exposures=exposures_zero,
            model_id="m", model_version="v", methodology_version="mv",
            covariance_version="cv", stress_scenario_version="sv"
        )
    assert "No covariance forecast matrix found" in str(exc.value)

    # 3. evaluate_portfolio_risk matrix missing in object store
    fc = CovarianceForecast("fc-1", "urn:karsa:risk:covariance:1", 1, datetime.utcnow())
    cov_repo.save_forecast(fc)
    with pytest.raises(InvalidValueException) as exc:
        risk_service.evaluate_portfolio_risk(
            evaluation_id="eval-1",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
            exposures=exposures_zero,
            model_id="m", model_version="v", methodology_version="mv",
            covariance_version="cv", stress_scenario_version="sv"
        )
    assert "Covariance matrix payload not found" in str(exc.value)

    # 4. evaluate_portfolio_risk indices out of bounds (diagonal fallback cov_val = 0.0)
    object_store.save_matrix("urn:karsa:risk:covariance:1", [[0.04]])
    exposures_two = [
        AssetExposure("urn:karsa:asset:1", 0.5, 50.0, "Tech"),
        AssetExposure("urn:karsa:asset:2", 0.5, 50.0, "Tech")
    ]
    rec = risk_service.evaluate_portfolio_risk(
        evaluation_id="eval-1",
        portfolio_snapshot_id="urn:karsa:portfolio:snapshot:1",
        exposures=exposures_two,
        model_id="m", model_version="v", methodology_version="mv",
        covariance_version="cv", stress_scenario_version="sv"
    )
    assert math.isclose(rec.risk_metrics[0].value, 1.645 * 0.15, rel_tol=1e-5)

    # 5. evaluate_portfolio_risk negative portfolio variance
    object_store.save_matrix("urn:karsa:risk:covariance:1", [[1.0, -10.0], [-10.0, 1.0]])
    with pytest.raises(NegativeEigenvalueException) as exc:
        risk_service.evaluate_portfolio_risk(
            evaluation_id="eval-neg-var",
            portfolio_snapshot_id="urn:karsa:portfolio:snapshot:neg-var",
            exposures=exposures_two,
            model_id="m", model_version="v", methodology_version="mv",
            covariance_version="cv", stress_scenario_version="sv"
        )
    assert "portfolio variance is negative" in str(exc.value)

    # 6. calculate_forecast empty asset_urns
    with pytest.raises(InvalidValueException) as exc:
        cov_service.calculate_forecast("fc-2", "urn:karsa:risk:covariance:2", [], {})
    assert "Asset URN list cannot be empty" in str(exc.value)

    # 7. calculate_forecast empty returns_data
    fc_res = cov_service.calculate_forecast("fc-2", "urn:karsa:risk:covariance:2", ["urn:a"], {})
    assert fc_res.universe_size == 1
    matrix = object_store.get_matrix("urn:karsa:risk:covariance:2")
    assert matrix[0][0] == 0.01

