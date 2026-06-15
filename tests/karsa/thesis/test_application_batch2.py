import pytest
from karsa.thesis.domain.models import Thesis, ThesisSnapshot
from karsa.thesis.domain.value_objects import LifecycleState
from karsa.thesis.domain.exceptions import InvalidLifecycleTransitionError
from karsa.thesis.application.services import (
    ThesisLifecycleService, ThesisChallengeEvaluationService,
    ThesisEvolutionService, ThesisAttributionService, ThesisReplayService
)

def test_lifecycle_service():
    svc = ThesisLifecycleService()
    thesis = Thesis("t1", "s1", LifecycleState.PROPOSED)
    
    thesis = svc.activate_thesis(thesis)
    assert thesis.current_status == LifecycleState.ACTIVE
    assert thesis.aggregate_version == 2
    
    thesis = svc.invalidate_thesis(thesis)
    assert thesis.current_status == LifecycleState.INVALIDATED
    assert thesis.aggregate_version == 3
    
    with pytest.raises(InvalidLifecycleTransitionError):
        svc.activate_thesis(thesis)

    with pytest.raises(InvalidLifecycleTransitionError):
        svc.invalidate_thesis(Thesis("t2", "s2", LifecycleState.PROPOSED))

def test_challenge_eval_service():
    svc = ThesisChallengeEvaluationService()
    thesis = Thesis("t1", "s1", LifecycleState.ACTIVE)
    assert svc.evaluate_challenge(thesis, "critical_123") is True
    assert svc.evaluate_challenge(thesis, "minor_123") is False

def test_evolution_service():
    svc = ThesisEvolutionService()
    thesis = Thesis("t1", "s1", LifecycleState.ACTIVE)
    transition = svc.evolve_thesis(thesis, "s2", "delta_1", "hash_abc")
    assert transition.transition_urn == "trans_delta_1"
    assert transition.delta.delta_manifest_hash == "hash_abc"
    assert thesis.current_snapshot_urn == "s2"
    assert thesis.aggregate_version == 2

def test_attribution_service():
    svc = ThesisAttributionService()
    res = svc.map_attribution("assump_1", "out_1")
    assert res == {"assumption": "assump_1", "outcome": "out_1"}

def test_replay_service():
    svc = ThesisReplayService()
    snap = ThesisSnapshot("snap_hash_123", 1, LifecycleState.ACTIVE, "reg_1", None, None, [])
    assert svc.verify_replay(snap, "snap_hash_123") is True
    assert svc.verify_replay(snap, "wrong_hash") is False
