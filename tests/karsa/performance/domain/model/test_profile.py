from karsa.performance.domain.model.profile import PerformanceProfileWindow
from karsa.performance.domain.model.value_objects import TargetIdentity, WindowIdentity, PredictionMetrics, InvestmentMetrics, EvaluationGrade

def test_profile_window_version_bump():
    target = TargetIdentity("orig1", "ORIGINATOR")
    window = WindowIdentity("MONTH", "2026-06")
    profile = PerformanceProfileWindow(target, window, PredictionMetrics(0,0,0), InvestmentMetrics(0,0))
    
    assert profile.aggregate_version == 1
    
    profile.apply_evaluation_grade(EvaluationGrade(1.0, 1.0, 1.0), PredictionMetrics(1.0, 0.0, 1), InvestmentMetrics(0,0))
    assert profile.aggregate_version == 2

def test_metric_bounds():
    # Tested within the metric registry rules usually, but object allows setting
    pm = PredictionMetrics(hit_rate=1.0, brier_score=0.5, evaluation_count=10)
    assert pm.hit_rate <= 1.0
    assert pm.hit_rate >= 0.0

def test_apply_evaluation_grade():
    target = TargetIdentity("orig1", "ORIGINATOR")
    window = WindowIdentity("MONTH", "2026-06")
    profile = PerformanceProfileWindow(target, window, PredictionMetrics(0,0,0), InvestmentMetrics(0,0))
    profile.apply_evaluation_grade(EvaluationGrade(1.0, 1.0, 1.0), PredictionMetrics(1.0, 0.0, 1), InvestmentMetrics(0,0))
    assert profile.prediction_metrics.evaluation_count == 1
