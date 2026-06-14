from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

from karsa.risk.services import RiskEvaluationService, StressTestingService, CovarianceForecastService
from karsa.risk.value_objects import AssetExposure, ValueAtRisk, ExpectedShortfall, ConcentrationRisk, LiquidityRisk
from karsa.risk.exceptions import (
    ImmutabilityViolationException,
    NegativeEigenvalueException,
    InvalidSnapshotURNException,
    InvalidValueException,
)

router = APIRouter(prefix="/risk", tags=["Risk Engine"])

_risk_evaluation_service: Optional[RiskEvaluationService] = None
_stress_testing_service: Optional[StressTestingService] = None
_covariance_forecast_service: Optional[CovarianceForecastService] = None

def get_risk_evaluation_service() -> RiskEvaluationService:
    if _risk_evaluation_service is None:
        raise RuntimeError("RiskEvaluationService not configured for API.")
    return _risk_evaluation_service

def get_stress_testing_service() -> StressTestingService:
    if _stress_testing_service is None:
        raise RuntimeError("StressTestingService not configured for API.")
    return _stress_testing_service

def get_covariance_forecast_service() -> CovarianceForecastService:
    if _covariance_forecast_service is None:
        raise RuntimeError("CovarianceForecastService not configured for API.")
    return _covariance_forecast_service

def configure_api(
    risk_service: RiskEvaluationService,
    stress_service: StressTestingService,
    cov_service: CovarianceForecastService
):
    global _risk_evaluation_service, _stress_testing_service, _covariance_forecast_service
    _risk_evaluation_service = risk_service
    _stress_testing_service = stress_service
    _covariance_forecast_service = cov_service

class AssetExposureSchema(BaseModel):
    asset_urn: str
    weight: float
    exposure_value: float
    sector: str

class RiskEvaluationCreateRequest(BaseModel):
    evaluation_id: str
    portfolio_snapshot_id: str
    exposures: List[AssetExposureSchema]
    model_id: str
    model_version: str
    methodology_version: str
    covariance_version: str
    stress_scenario_version: str

class StressEvaluationCreateRequest(BaseModel):
    stress_evaluation_id: str
    portfolio_snapshot_id: str
    scenario_urn: str
    exposures: List[AssetExposureSchema]
    shocks: Dict[str, float]

class CovarianceForecastCreateRequest(BaseModel):
    forecast_id: str
    matrix_urn: str
    asset_urns: List[str]
    returns_data: Dict[str, List[float]]

@router.post("/evaluations", status_code=status.HTTP_201_CREATED)
def create_risk_evaluation(
    request: RiskEvaluationCreateRequest,
    service: RiskEvaluationService = Depends(get_risk_evaluation_service)
):
    try:
        exposures = [
            AssetExposure(
                asset_urn=e.asset_urn,
                weight=e.weight,
                exposure_value=e.exposure_value,
                sector=e.sector
            ) for e in request.exposures
        ]

        record = service.evaluate_portfolio_risk(
            evaluation_id=request.evaluation_id,
            portfolio_snapshot_id=request.portfolio_snapshot_id,
            exposures=exposures,
            model_id=request.model_id,
            model_version=request.model_version,
            methodology_version=request.methodology_version,
            covariance_version=request.covariance_version,
            stress_scenario_version=request.stress_scenario_version
        )

        return {
            "evaluation_id": record.evaluation_id,
            "portfolio_snapshot_id": record.portfolio_snapshot_id,
            "created_at": record.created_at.isoformat()
        }
    except ImmutabilityViolationException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NegativeEigenvalueException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidSnapshotURNException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidValueException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/evaluations/{evaluation_id}")
def get_risk_evaluation(
    evaluation_id: str,
    service: RiskEvaluationService = Depends(get_risk_evaluation_service)
):
    record = service.record_repo.get_evaluation_by_id(evaluation_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Risk evaluation record {evaluation_id} not found.")

    return {
        "evaluation_id": record.evaluation_id,
        "portfolio_snapshot_id": record.portfolio_snapshot_id,
        "model_id": record.model_id,
        "model_version": record.model_version,
        "methodology_version": record.methodology_version,
        "covariance_version": record.covariance_version,
        "stress_scenario_version": record.stress_scenario_version,
        "regime_state_urn": record.regime_state_urn,
        "risk_metrics": [
            {"confidence_level": m.confidence_level, "horizon_days": m.horizon_days, "value": m.value}
            for m in record.risk_metrics
        ],
        "expected_shortfalls": [
            {"confidence_level": m.confidence_level, "horizon_days": m.horizon_days, "value": m.value}
            for m in record.expected_shortfalls
        ],
        "exposures": [
            {"asset_urn": m.asset_urn, "weight": m.weight, "exposure_value": m.exposure_value, "sector": m.sector}
            for m in record.exposures
        ],
        "concentration_stats": {
            "hhi": record.concentration_risk.hhi,
            "gini": record.concentration_risk.gini,
            "top_5_weight": record.concentration_risk.top_5_weight
        },
        "liquidity_metrics": [
            {"asset_urn": m.asset_urn, "days_to_liquidate": m.days_to_liquidate, "liquidation_scenario_percent": m.liquidation_scenario_percent}
            for m in record.liquidity_risks
        ],
        "created_at": record.created_at.isoformat()
    }

@router.post("/stress-tests", status_code=status.HTTP_201_CREATED)
def create_stress_evaluation(
    request: StressEvaluationCreateRequest,
    service: StressTestingService = Depends(get_stress_testing_service)
):
    try:
        exposures = [
            AssetExposure(
                asset_urn=e.asset_urn,
                weight=e.weight,
                exposure_value=e.exposure_value,
                sector=e.sector
            ) for e in request.exposures
        ]

        record = service.evaluate_stress(
            stress_evaluation_id=request.stress_evaluation_id,
            portfolio_snapshot_id=request.portfolio_snapshot_id,
            scenario_urn=request.scenario_urn,
            exposures=exposures,
            shocks=request.shocks
        )

        return {
            "stress_evaluation_id": record.stress_evaluation_id,
            "portfolio_snapshot_id": record.portfolio_snapshot_id,
            "scenario_urn": record.scenario_urn,
            "portfolio_impact_percent": record.shock_results.portfolio_impact_percent,
            "created_at": record.created_at.isoformat()
        }
    except ImmutabilityViolationException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidSnapshotURNException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidValueException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/stress-tests/{stress_evaluation_id}")
def get_stress_evaluation(
    stress_evaluation_id: str,
    service: StressTestingService = Depends(get_stress_testing_service)
):
    record = service.stress_repo.get_stress_evaluation_by_id(stress_evaluation_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Stress evaluation record {stress_evaluation_id} not found.")

    return {
        "stress_evaluation_id": record.stress_evaluation_id,
        "portfolio_snapshot_id": record.portfolio_snapshot_id,
        "scenario_urn": record.scenario_urn,
        "shock_results": {
            "scenario_urn": record.shock_results.scenario_urn,
            "portfolio_impact_percent": record.shock_results.portfolio_impact_percent,
            "shock_results": record.shock_results.shock_results
        },
        "created_at": record.created_at.isoformat()
    }

@router.post("/covariance-forecasts", status_code=status.HTTP_201_CREATED)
def create_covariance_forecast(
    request: CovarianceForecastCreateRequest,
    service: CovarianceForecastService = Depends(get_covariance_forecast_service)
):
    try:
        record = service.calculate_forecast(
            forecast_id=request.forecast_id,
            matrix_urn=request.matrix_urn,
            asset_urns=request.asset_urns,
            returns_data=request.returns_data
        )

        return {
            "forecast_id": record.forecast_id,
            "matrix_urn": record.matrix_urn,
            "universe_size": record.universe_size,
            "created_at": record.created_at.isoformat()
        }
    except ImmutabilityViolationException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NegativeEigenvalueException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidValueException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/covariance-forecasts/latest")
def get_latest_covariance_forecast(
    service: CovarianceForecastService = Depends(get_covariance_forecast_service)
):
    record = service.cov_repo.get_latest_forecast()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No covariance forecast found.")

    return {
        "forecast_id": record.forecast_id,
        "matrix_urn": record.matrix_urn,
        "universe_size": record.universe_size,
        "created_at": record.created_at.isoformat()
    }
