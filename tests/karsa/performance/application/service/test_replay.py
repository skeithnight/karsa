from karsa.performance.events.performance_events import ThesisEvaluatedPayload
from karsa.performance.domain.model.value_objects import EvaluationGrade, PredictionMetrics, InvestmentMetrics, TargetIdentity, WindowIdentity
from karsa.performance.domain.model.profile import PerformanceProfileWindow
from karsa.performance.domain.registry.metric_registry import MetricRegistry
import random

def test_rebuild_from_thesis_evaluated_events():
    random.seed(42)
    events = []
    
    # 1. Generate 1000 events
    for i in range(1000):
        expected = random.uniform(0.0, 1.0)
        actual = random.uniform(0.0, 1.0)
        diff = abs(expected - actual)
        pred_score = max(0.0, 1.0 - diff)
        
        payload = ThesisEvaluatedPayload(
            thesis_id=f"t_{i}",
            evaluation_grade={"prediction_score": pred_score, "investment_score": 0.0, "timing_score": 1.0},
            metric_version="v1",
            algorithm_hash="hash_v1_basic",
            evaluated_at="2026-06-15"
        )
        events.append(payload)

    # 5. Independently calculate expected metrics
    expected_hit_rate = 0.0
    expected_brier = 0.0
    expected_count = 0
    
    for e in events:
        score = e.evaluation_grade["prediction_score"]
        expected_count += 1
        hit = 1.0 if score >= 0.5 else 0.0
        expected_hit_rate = ((expected_hit_rate * (expected_count - 1)) + hit) / expected_count
        brier_penalty = (1.0 - score) ** 2
        expected_brier = ((expected_brier * (expected_count - 1)) + brier_penalty) / expected_count
        expected_brier = max(0.0, min(1.0, expected_brier))

    # 3. Replay events through the rebuild mechanism
    target = TargetIdentity("orig1", "ORIGINATOR")
    window = WindowIdentity("MONTH", "2026-06")
    profile = PerformanceProfileWindow(target, window, PredictionMetrics(0.0, 0.0, 0), InvestmentMetrics(0.0, 0.0))
    
    # Replay loop simulation
    for e in events:
        formula = MetricRegistry.get_formula(e.metric_version)
        grade = EvaluationGrade(**e.evaluation_grade)
        
        new_pred = formula.calculate_prediction(grade, profile.prediction_metrics)
        new_inv = formula.calculate_investment(grade, profile.investment_metrics)
        profile.apply_evaluation_grade(grade, new_pred, new_inv)

    # 6. Compare & 7. Assert
    assert profile.prediction_metrics.evaluation_count == 1000
    assert abs(profile.prediction_metrics.hit_rate - expected_hit_rate) < 1e-9
    assert abs(profile.prediction_metrics.brier_score - expected_brier) < 1e-9
    
    # Validation 
    assert profile.aggregate_version == 1001 # 1 for init + 1000 increments
