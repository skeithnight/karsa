from unittest.mock import MagicMock
from karsa.performance.application.saga.fanout_saga import PerformanceFanOutSaga
from karsa.shared.events.envelope import PlatformEventEnvelope
from karsa.performance.events.performance_events import ThesisEvaluatedPayload
import uuid, time

def test_fanout_saga_generates_three_commands():
    bus = MagicMock()
    saga = PerformanceFanOutSaga(bus)
    
    payload = ThesisEvaluatedPayload("t1", {"prediction_score": 1.0, "investment_score": 0.0, "timing_score": 1.0}, "v1", "hash", "2026-06-15")
    envelope = PlatformEventEnvelope(str(uuid.uuid4()), "ThesisEvaluatedEvent", "", "", "ThesisEvaluation", "t1", 1, str(int(time.time())), "1.0", payload.__dict__)
    
    saga.handle(envelope)
    
    assert bus.publish_command.call_count == 3

def test_window_calculation():
    bus = MagicMock()
    saga = PerformanceFanOutSaga(bus)
    payload = ThesisEvaluatedPayload("t1", {"prediction_score": 1.0, "investment_score": 0.0, "timing_score": 1.0}, "v1", "hash", "2026-06-15")
    envelope = PlatformEventEnvelope(str(uuid.uuid4()), "ThesisEvaluatedEvent", "", "", "ThesisEvaluation", "t1", 1, str(int(time.time())), "1.0", payload.__dict__)
    saga.handle(envelope)
    
    cmd = bus.publish_command.call_args_list[0][0][0]
    assert cmd.window_identity.period_value == "2026-06"
