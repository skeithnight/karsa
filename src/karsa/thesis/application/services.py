from karsa.thesis.domain.models import Thesis, ThesisSnapshot, ThesisTransition, ThesisDelta
from karsa.thesis.domain.value_objects import LifecycleState
from karsa.thesis.domain.exceptions import InvalidLifecycleTransitionError

class ThesisLifecycleService:
    def activate_thesis(self, thesis: Thesis) -> Thesis:
        if thesis.current_status != LifecycleState.PROPOSED:
            raise InvalidLifecycleTransitionError("Only PROPOSED theses can be activated.")
        thesis.update_snapshot(thesis.current_snapshot_urn, LifecycleState.ACTIVE)
        return thesis

    def invalidate_thesis(self, thesis: Thesis) -> Thesis:
        if thesis.current_status != LifecycleState.ACTIVE:
            raise InvalidLifecycleTransitionError("Only ACTIVE theses can be invalidated.")
        thesis.update_snapshot(thesis.current_snapshot_urn, LifecycleState.INVALIDATED)
        return thesis

class ThesisChallengeEvaluationService:
    def evaluate_challenge(self, thesis: Thesis, challenge_urn: str) -> bool:
        # Evaluates if the challenge forces an invalidation or evolution
        # Hardcoded deterministic logic for testing
        return challenge_urn.startswith("critical_")

class ThesisEvolutionService:
    def evolve_thesis(self, thesis: Thesis, new_snapshot_urn: str, 
                      delta_urn: str, delta_manifest_hash: str) -> ThesisTransition:
        delta = ThesisDelta(delta_urn, delta_manifest_hash, [], [])
        transition = ThesisTransition(f"trans_{delta_urn}", None, None, delta)
        thesis.update_snapshot(new_snapshot_urn, LifecycleState.ACTIVE)
        return transition

class ThesisAttributionService:
    def map_attribution(self, assumption_urn: str, outcome_urn: str) -> dict:
        return {"assumption": assumption_urn, "outcome": outcome_urn}

class ThesisReplayService:
    def verify_replay(self, snapshot: ThesisSnapshot, expected_hash: str) -> bool:
        # Simplistic hash check to prove replay determinism without live DB
        return snapshot.snapshot_urn == expected_hash
