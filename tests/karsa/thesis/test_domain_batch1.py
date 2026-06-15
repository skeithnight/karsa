import pytest
from karsa.thesis.domain.value_objects import (
    LifecycleState, AssumptionLifecycleState, ReviewReference, 
    CalibrationReference, AssumptionOutcomeReference
)
from karsa.thesis.domain.models import (
    ThesisAssumptionIdentity, ThesisAssumptionVersion, ThesisDelta,
    ThesisTransition, ThesisSnapshot, Thesis
)
from karsa.thesis.domain.exceptions import LineageCycleError
from karsa.thesis.domain.lineage import validate_transition_lineage, validate_snapshot_lineage
from karsa.thesis.domain.events import (
    ThesisProposedEvent, ThesisActivatedEvent, ThesisChallengedEvent,
    ThesisRefinedEvent, ThesisInvalidatedEvent, ThesisRetiredEvent
)

def test_value_objects():
    rev = ReviewReference("rev_1", "hash")
    assert rev.review_urn == "rev_1"
    cal = CalibrationReference("cal_1", "hash")
    assert cal.calibration_urn == "cal_1"
    out = AssumptionOutcomeReference("out_1", "1M", "1Y", "perf", "hash")
    assert out.outcome_reference_urn == "out_1"

def test_models():
    ident = ThesisAssumptionIdentity("assump_1")
    assert ident.assumption_urn == "assump_1"
    
    ver = ThesisAssumptionVersion("assump_1", 1, "statement", 0.8, AssumptionLifecycleState.ACTIVE, "hash")
    assert ver.assumption_version == 1
    
    delta = ThesisDelta("delta_1", "hash", [], [])
    trans = ThesisTransition("trans_1", None, None, delta)
    assert trans.transition_urn == "trans_1"
    
    snap = ThesisSnapshot("snap_1", 1, LifecycleState.ACTIVE, "reg_1", None, None, [ver])
    assert snap.snapshot_version == 1
    
    thesis = Thesis("thesis_1", "snap_1", LifecycleState.ACTIVE)
    assert thesis.aggregate_version == 1
    
    thesis.update_snapshot("snap_2", LifecycleState.REFINING)
    assert thesis.aggregate_version == 2
    assert thesis.current_status == LifecycleState.REFINING

def test_events():
    ev = ThesisProposedEvent("t1", "s1")
    assert ev.thesis_urn == "t1"
    ev2 = ThesisActivatedEvent("t1", "s1")
    assert ev2.thesis_urn == "t1"
    ev3 = ThesisChallengedEvent("t1", "c1")
    assert ev3.thesis_urn == "t1"
    ev4 = ThesisRefinedEvent("t1", "tr1", "hash")
    assert ev4.thesis_urn == "t1"
    ev5 = ThesisInvalidatedEvent("t1")
    assert ev5.thesis_urn == "t1"
    ev6 = ThesisRetiredEvent("t1")
    assert ev6.thesis_urn == "t1"

def test_lineage():
    delta = ThesisDelta("delta_1", "hash", [], [])
    t1 = ThesisTransition("trans_1", None, None, delta)
    t2 = ThesisTransition("trans_1", None, None, delta) # duplicate to cause cycle
    
    with pytest.raises(LineageCycleError):
        validate_transition_lineage([t1, t2])
        
    s1 = ThesisSnapshot("snap_1", 1, LifecycleState.ACTIVE, "reg_1", None, None, [])
    s2 = ThesisSnapshot("snap_1", 1, LifecycleState.ACTIVE, "reg_1", None, None, [])
    
    with pytest.raises(LineageCycleError):
        validate_snapshot_lineage([s1, s2])

def test_lineage_success():
    delta = ThesisDelta("delta_1", "hash", [], [])
    t1 = ThesisTransition("trans_1", None, None, delta)
    t2 = ThesisTransition("trans_2", "trans_1", None, delta)
    validate_transition_lineage([t1, t2])

    s1 = ThesisSnapshot("snap_1", 1, LifecycleState.ACTIVE, "reg_1", None, None, [])
    s2 = ThesisSnapshot("snap_2", 2, LifecycleState.ACTIVE, "reg_1", "snap_1", None, [])
    validate_snapshot_lineage([s1, s2])
