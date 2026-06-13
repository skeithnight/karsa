from dataclasses import dataclass
from typing import Callable
from karsa.performance.domain.model.value_objects import EvaluationGrade, PredictionMetrics, InvestmentMetrics

@dataclass(frozen=True)
class MetricDefinition:
    algorithm_hash: str
    calculate_prediction: Callable[[EvaluationGrade, PredictionMetrics], PredictionMetrics]
    calculate_investment: Callable[[EvaluationGrade, InvestmentMetrics], InvestmentMetrics]

class MetricRegistry:
    _registry = {}

    @classmethod
    def register(cls, version: str, definition: MetricDefinition):
        cls._registry[version] = definition

    @classmethod
    def get_formula(cls, version: str) -> MetricDefinition:
        if version not in cls._registry:
            raise ValueError(f"MetricVersionNotFoundError: {version}")
        return cls._registry[version]

def _calc_pred_v1(grade: EvaluationGrade, old: PredictionMetrics) -> PredictionMetrics:
    new_count = old.evaluation_count + 1
    hit = 1.0 if grade.prediction_score >= 0.5 else 0.0
    new_hit_rate = ((old.hit_rate * old.evaluation_count) + hit) / new_count
    # basic brier tracking
    brier_penalty = (1.0 - grade.prediction_score) ** 2
    new_brier = ((old.brier_score * old.evaluation_count) + brier_penalty) / new_count
    return PredictionMetrics(hit_rate=new_hit_rate, brier_score=max(0.0, min(1.0, new_brier)), evaluation_count=new_count)

def _calc_inv_v1(grade: EvaluationGrade, old: InvestmentMetrics) -> InvestmentMetrics:
    return InvestmentMetrics(average_roi=0.0, capital_efficiency_score=0.0)

MetricRegistry.register("v1", MetricDefinition("hash_v1_basic", _calc_pred_v1, _calc_inv_v1))
