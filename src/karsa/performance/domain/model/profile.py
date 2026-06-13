from karsa.shared.domain.aggregate import VersionedAggregate
from .value_objects import TargetIdentity, WindowIdentity, PredictionMetrics, InvestmentMetrics, EvaluationGrade

class PerformanceProfileWindow(VersionedAggregate):
    def __init__(self, target_identity: TargetIdentity, window_identity: WindowIdentity,
                 prediction_metrics: PredictionMetrics, investment_metrics: InvestmentMetrics,
                 version: int = 1):
        super().__init__(aggregate_version=version)
        self.target_identity = target_identity
        self.window_identity = window_identity
        self.prediction_metrics = prediction_metrics
        self.investment_metrics = investment_metrics

    def apply_evaluation_grade(self, grade: EvaluationGrade, new_prediction_metrics: PredictionMetrics, new_investment_metrics: InvestmentMetrics):
        self.prediction_metrics = new_prediction_metrics
        self.investment_metrics = new_investment_metrics
        self.increment_version()
