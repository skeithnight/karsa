from dataclasses import dataclass
from karsa.performance.domain.model.value_objects import TargetIdentity, WindowIdentity, EvaluationGrade

@dataclass
class EvaluateThesisCommand:
    thesis_id: str
    expected_outcome: float
    actual_outcome: float
    resolution_date: str

@dataclass
class ApplyEvaluationCommand:
    target_identity: TargetIdentity
    window_identity: WindowIdentity
    evaluation_grade: EvaluationGrade
    thesis_id: str

@dataclass
class RebuildPerformanceProfilesCommand:
    pass
