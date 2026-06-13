import pytest
from karsa.performance.domain.registry.metric_registry import MetricRegistry
from karsa.performance.domain.model.value_objects import EvaluationGrade, PredictionMetrics

def test_metric_lookup():
    formula = MetricRegistry.get_formula("v1")
    assert formula is not None

def test_metric_version_resolution():
    with pytest.raises(ValueError):
        MetricRegistry.get_formula("nonexistent_v99")

def test_algorithm_hash_consistency():
    formula = MetricRegistry.get_formula("v1")
    assert formula.algorithm_hash == "hash_v1_basic"
    
def test_incremental_brier_calculation_accuracy():
    formula = MetricRegistry.get_formula("v1")
    grade = EvaluationGrade(prediction_score=0.2, investment_score=0, timing_score=0)
    old = PredictionMetrics(hit_rate=1.0, brier_score=0.0, evaluation_count=1)
    
    new_metrics = formula.calculate_prediction(grade, old)
    assert new_metrics.evaluation_count == 2
    # old hit = 1*1, new hit = 0 (since pred_score < 0.5), sum=1, rate=0.5
    assert new_metrics.hit_rate == 0.5
    # old brier = 0, penalty = (1-0.2)^2 = 0.64. sum=0.64. brier=0.32
    assert abs(new_metrics.brier_score - 0.32) < 0.001
