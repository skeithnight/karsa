from karsa.shared.infrastructure.uow import UnitOfWork
from karsa.performance.domain.model.evaluation import ThesisEvaluationService
from karsa.performance.application.commands import EvaluateThesisCommand, ApplyEvaluationCommand
from karsa.performance.events.performance_events import build_thesis_evaluated_event, ThesisEvaluatedPayload, build_profile_updated_event, PerformanceProfileUpdatedPayload
from karsa.performance.infrastructure.storage.profile_repository import ProfileRepository
from karsa.performance.domain.model.profile import PerformanceProfileWindow
from karsa.performance.domain.model.value_objects import PredictionMetrics, InvestmentMetrics
from karsa.performance.domain.registry.metric_registry import MetricRegistry
from karsa.shared.infrastructure.outbox import OutboxRecord
import json
from dataclasses import asdict

class PerformanceApplicationService:
    def __init__(self, uow: UnitOfWork, profile_repo: ProfileRepository):
        self.uow = uow
        self.profile_repo = profile_repo

    def evaluate_thesis(self, cmd: EvaluateThesisCommand):
        grade = ThesisEvaluationService.evaluate(cmd.expected_outcome, cmd.actual_outcome, cmd.resolution_date)
        formula_def = MetricRegistry.get_formula("v1")
        
        event = build_thesis_evaluated_event(ThesisEvaluatedPayload(
            thesis_id=cmd.thesis_id,
            evaluation_grade=grade.__dict__,
            metric_version="v1",
            algorithm_hash=formula_def.algorithm_hash,
            evaluated_at=cmd.resolution_date
        ))
        
        with self.uow:
            # Event Outbox pattern
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)),
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)

    def apply_evaluation_to_profile(self, cmd: ApplyEvaluationCommand):
        with self.uow:
            profile = self.profile_repo.get_by_identity(cmd.target_identity, cmd.window_identity)
            if not profile:
                profile = PerformanceProfileWindow(
                    target_identity=cmd.target_identity,
                    window_identity=cmd.window_identity,
                    prediction_metrics=PredictionMetrics(0.0, 0.0, 0),
                    investment_metrics=InvestmentMetrics(0.0, 0.0)
                )
            
            formula = MetricRegistry.get_formula("v1")
            new_pred = formula.calculate_prediction(cmd.evaluation_grade, profile.prediction_metrics)
            new_inv = formula.calculate_investment(cmd.evaluation_grade, profile.investment_metrics)
            
            profile.apply_evaluation_grade(cmd.evaluation_grade, new_pred, new_inv)
            self.profile_repo.save(profile)
            
            event = build_profile_updated_event(PerformanceProfileUpdatedPayload(
                target_identity=cmd.target_identity.__dict__,
                window_identity=cmd.window_identity.__dict__,
                prediction_metrics=new_pred.__dict__,
                investment_metrics=new_inv.__dict__,
                update_reason_thesis_id=cmd.thesis_id
            ))
            
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)),
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)
