from karsa.performance.events.performance_events import ThesisEvaluatedPayload
from karsa.performance.application.commands import ApplyEvaluationCommand
from karsa.performance.domain.model.value_objects import TargetIdentity, WindowIdentity, EvaluationGrade
import json

class PerformanceFanOutSaga:
    def __init__(self, message_bus):
        self.message_bus = message_bus

    def handle(self, event_envelope):
        if event_envelope.event_type != "ThesisEvaluatedEvent":
            return
            
        payload = ThesisEvaluatedPayload(**event_envelope.payload)
        
        # In a real system, we look up the originator, worker, strategy from the context
        # For simplicity, we assume we extract these:
        targets = [
            TargetIdentity(target_id="originator_1", target_type="ORIGINATOR"),
            TargetIdentity(target_id="worker_1", target_type="WORKER"),
            TargetIdentity(target_id="strategy_1", target_type="STRATEGY")
        ]
        
        window = WindowIdentity(period_type="MONTH", period_value=payload.evaluated_at[:7])
        grade = EvaluationGrade(**payload.evaluation_grade)
        
        for t in targets:
            cmd = ApplyEvaluationCommand(target_identity=t, window_identity=window, evaluation_grade=grade, thesis_id=payload.thesis_id)
            self.message_bus.publish_command(cmd)
