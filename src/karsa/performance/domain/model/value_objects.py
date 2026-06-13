from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class TargetIdentity:
    target_id: str
    target_type: str

@dataclass(frozen=True)
class WindowIdentity:
    period_type: str
    period_value: str

@dataclass(frozen=True)
class PredictionMetrics:
    hit_rate: float
    brier_score: float
    evaluation_count: int

@dataclass(frozen=True)
class InvestmentMetrics:
    average_roi: float
    capital_efficiency_score: float

@dataclass(frozen=True)
class EvaluationGrade:
    prediction_score: float
    investment_score: float
    timing_score: float

@dataclass(frozen=True)
class ThesisScoreRecord:
    thesis_id: str
    evaluation_grade: EvaluationGrade
