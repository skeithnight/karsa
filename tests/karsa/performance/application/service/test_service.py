from unittest.mock import MagicMock
from karsa.performance.application.service.performance_application_service import PerformanceApplicationService
from karsa.performance.application.commands import EvaluateThesisCommand, ApplyEvaluationCommand
from karsa.performance.domain.model.value_objects import TargetIdentity, WindowIdentity, EvaluationGrade
from karsa.performance.domain.model.evaluation import ThesisEvaluationService
from karsa.shared.infrastructure.uow import UnitOfWork

def test_evaluation_service_grade_computation():
    grade = ThesisEvaluationService.evaluate(expected_outcome=0.4, actual_outcome=0.45, resolution_date="2026-06-01")
    assert grade.prediction_score == 0.95

def test_evaluation_service_deterministic_output():
    grade1 = ThesisEvaluationService.evaluate(0.4, 0.45, "2026-06-01")
    grade2 = ThesisEvaluationService.evaluate(0.4, 0.45, "2026-06-01")
    assert grade1 == grade2

def test_evaluate_to_outbox():
    uow = MagicMock()
    repo = MagicMock()
    uow.__enter__.return_value = uow
    svc = PerformanceApplicationService(uow, repo)
    cmd = EvaluateThesisCommand("t1", 0.4, 0.4, "2026-06-01")
    svc.evaluate_thesis(cmd)
    
    uow.outbox_repository.save.assert_called_once()
