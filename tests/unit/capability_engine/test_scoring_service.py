"""Tests for CapabilityScoringService -- Sprint-11. Transaction B.

Covers:
- score calculation
- algorithm version handling
- OCC conflict retry
- evaluation ordering rejection
- version transition handling
"""

import pytest
from datetime import datetime

from karsa.capability_engine.application.capability_scoring_service import (
    CapabilityScoringService,
    ScoringCommand,
    ScoringResult,
    DEFAULT_MAX_OCC_RETRIES,
    SUSPEND_THRESHOLD,
    UNSUSPEND_THRESHOLD,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.events.capability_events import (
    CapabilityHealthScoreUpdatedEvent,
    GovernanceCapabilitySuspendedEvent,
    GovernanceCapabilityUnsuspendedEvent,
)
from karsa.capability_engine.domain.exceptions import (
    EvaluationOrderingError,
    InvalidHealthScoreError,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryCapabilityHealthScoreRepository,
    InMemoryOutboxRepository,
    InMemoryScoreHistoryRepository,
)


# --- Fixtures ---

def _make_components():
    """Build a valid set of score components."""
    return [
        CapabilityScoreComponent(
            component_name="EXECUTION_QUALITY",
            component_score=0.8,
            weight=0.25,
            evaluation_count=1,
            confidence=0.9,
        ),
        CapabilityScoreComponent(
            component_name="ATTRIBUTION_ALIGNMENT",
            component_score=0.7,
            weight=0.25,
            evaluation_count=1,
            confidence=0.85,
        ),
        CapabilityScoreComponent(
            component_name="REVIEW_SENTIMENT",
            component_score=0.6,
            weight=0.25,
            evaluation_count=1,
            confidence=0.8,
        ),
        CapabilityScoreComponent(
            component_name="REGIME_FITNESS",
            component_score=0.9,
            weight=0.25,
            evaluation_count=1,
            confidence=0.95,
        ),
    ]


def _make_command(**overrides) -> ScoringCommand:
    defaults = dict(
        capability_family_id="family-uuid-001",
        evaluation_id="eval-uuid-001",
        evaluation_sequence=1,
        capability_version_id="ver-uuid-001",
        score=0.75,
        components=_make_components(),
        algorithm_version="v1.0",
        capability_urn="urn:karsa:capability:ns:test:v1",
    )
    defaults.update(overrides)
    return ScoringCommand(**defaults)


def _make_service(max_retries=DEFAULT_MAX_OCC_RETRIES):
    health_repo = InMemoryCapabilityHealthScoreRepository()
    history_repo = InMemoryScoreHistoryRepository()
    outbox_repo = InMemoryOutboxRepository()
    service = CapabilityScoringService(
        health_score_repo=health_repo,
        score_history_repo=history_repo,
        outbox_repo=outbox_repo,
        max_occ_retries=max_retries,
    )
    return service, health_repo, history_repo, outbox_repo


# --- Tests: Score Calculation ---

class TestScoreCalculation:
    """ADR-132: Health score aggregate updates."""

    def test_first_evaluation_creates_health_score(self):
        service, health_repo, _, _ = _make_service()
        cmd = _make_command()
        result = service.record_evaluation(cmd)
        assert result.success is True
        assert result.new_score == 0.75
        assert result.previous_score == 0.5  # default neutral

    def test_evaluation_persists_score(self):
        service, health_repo, _, _ = _make_service()
        cmd = _make_command()
        result = service.record_evaluation(cmd)
        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved is not None
        assert saved.current_score == 0.75
        assert saved.evaluation_count == 1

    def test_evaluation_creates_history_entry(self):
        service, _, history_repo, _ = _make_service()
        cmd = _make_command()
        result = service.record_evaluation(cmd)
        history = history_repo.get_by_family("family-uuid-001")
        assert len(history) == 1
        assert history[0].score == 0.75
        assert history[0].evaluation_sequence == 1

    def test_sequential_evaluations_accumulate(self):
        service, health_repo, history_repo, _ = _make_service()

        cmd1 = _make_command(evaluation_sequence=1, score=0.6)
        service.record_evaluation(cmd1)

        cmd2 = _make_command(evaluation_id="eval-002", evaluation_sequence=2, score=0.8)
        result = service.record_evaluation(cmd2)

        assert result.success is True
        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved.current_score == 0.8
        assert saved.evaluation_count == 2

        history = history_repo.get_by_family("family-uuid-001")
        assert len(history) == 2

    def test_evaluation_emits_updated_event(self):
        service, _, _, _ = _make_service()
        cmd = _make_command()
        result = service.record_evaluation(cmd)
        assert len(result.events) >= 1
        updated_event = result.events[0]
        assert isinstance(updated_event, CapabilityHealthScoreUpdatedEvent)
        assert updated_event.new_score == 0.75
        assert updated_event.previous_score == 0.5


# --- Tests: Algorithm Version Handling ---

class TestAlgorithmVersionHandling:
    """ADR-134: Scoring algorithm versioning."""

    def test_algorithm_version_recorded_on_aggregate(self):
        service, health_repo, _, _ = _make_service()
        cmd = _make_command(algorithm_version="v2.0")
        result = service.record_evaluation(cmd)
        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved.algorithm_version == "v2.0"

    def test_algorithm_version_recorded_in_history(self):
        service, _, history_repo, _ = _make_service()
        cmd = _make_command(algorithm_version="v2.0")
        result = service.record_evaluation(cmd)
        history = history_repo.get_by_family("family-uuid-001")
        assert history[0].algorithm_version == "v2.0"

    def test_algorithm_version_change_across_evaluations(self):
        service, health_repo, _, _ = _make_service()

        cmd1 = _make_command(evaluation_sequence=1, algorithm_version="v1.0")
        service.record_evaluation(cmd1)

        cmd2 = _make_command(evaluation_id="eval-002", evaluation_sequence=2, algorithm_version="v2.0")
        service.record_evaluation(cmd2)

        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved.algorithm_version == "v2.0"


# --- Tests: OCC Conflict Retry ---

class TestOCCConflictRetry:
    """ADR-132: OCC retry support."""

    def test_occ_retry_succeeds_on_first_attempt(self):
        service, _, _, _ = _make_service()
        cmd = _make_command()
        result = service.record_evaluation(cmd)
        assert result.success is True
        assert result.occ_retries == 0

    def test_occ_conflict_triggers_retry(self):
        """Simulate OCC conflict: concurrent version bump between load and save."""
        health_repo = InMemoryCapabilityHealthScoreRepository()
        history_repo = InMemoryScoreHistoryRepository()
        outbox_repo = InMemoryOutboxRepository()

        service = CapabilityScoringService(
            health_score_repo=health_repo,
            score_history_repo=history_repo,
            outbox_repo=outbox_repo,
            max_occ_retries=3,
        )

        # Pre-populate with a health score at version 5
        existing = CapabilityHealthScore(
            health_score_id="existing-id",
            capability_family_id="family-uuid-001",
            current_score=0.5,
            aggregate_version=5,
        )
        health_repo.save(existing)

        # Intercept: after each load, bump the stored version to simulate
        # a concurrent writer. This ensures the OCC check always fails.
        original_get = health_repo.get_by_family_id
        call_count = {"n": 0}

        def intercepting_get(family_id):
            result = original_get(family_id)
            if result is not None:
                call_count["n"] += 1
                # Simulate concurrent update: bump stored version
                concurrent = CapabilityHealthScore(
                    health_score_id="existing-id",
                    capability_family_id=family_id,
                    current_score=0.55,
                    aggregate_version=result.aggregate_version + 1,
                )
                health_repo._store[family_id] = concurrent
            return result

        health_repo.get_by_family_id = intercepting_get

        cmd = _make_command(evaluation_sequence=1)
        result = service.record_evaluation(cmd)
        assert result.success is False
        assert result.occ_retries == 3
        assert call_count["n"] == 4  # 1 initial + 3 retries

    def test_occ_retry_count_respects_max(self):
        service, _, _, _ = _make_service(max_retries=2)
        health_repo = service._health_score_repo

        existing = CapabilityHealthScore(
            health_score_id="existing",
            capability_family_id="family-uuid-001",
            aggregate_version=5,
        )
        health_repo.save(existing)

        # Intercept: bump stored version after each load
        original_get = health_repo.get_by_family_id

        def intercepting_get(family_id):
            result = original_get(family_id)
            if result is not None:
                concurrent = CapabilityHealthScore(
                    health_score_id="existing",
                    capability_family_id=family_id,
                    current_score=0.55,
                    aggregate_version=result.aggregate_version + 1,
                )
                health_repo._store[family_id] = concurrent
            return result

        health_repo.get_by_family_id = intercepting_get

        cmd = _make_command(evaluation_sequence=1)
        result = service.record_evaluation(cmd)
        assert result.success is False
        assert result.occ_retries == 2


# --- Tests: Evaluation Ordering Rejection ---

class TestEvaluationOrderingRejection:
    """ADR-136: Monotonic evaluation ordering."""

    def test_duplicate_sequence_rejected(self):
        service, _, _, _ = _make_service()
        cmd1 = _make_command(evaluation_sequence=1)
        service.record_evaluation(cmd1)

        cmd2 = _make_command(evaluation_id="eval-002", evaluation_sequence=1)
        with pytest.raises(EvaluationOrderingError, match="must be >"):
            service.record_evaluation(cmd2)

    def test_lower_sequence_rejected(self):
        service, _, _, _ = _make_service()
        cmd1 = _make_command(evaluation_sequence=5)
        service.record_evaluation(cmd1)

        cmd2 = _make_command(evaluation_id="eval-002", evaluation_sequence=3)
        with pytest.raises(EvaluationOrderingError, match="must be >"):
            service.record_evaluation(cmd2)

    def test_higher_sequence_accepted(self):
        service, _, _, _ = _make_service()
        cmd1 = _make_command(evaluation_sequence=1)
        service.record_evaluation(cmd1)

        cmd2 = _make_command(evaluation_id="eval-002", evaluation_sequence=2)
        result = service.record_evaluation(cmd2)
        assert result.success is True

    def test_ordering_enforced_across_history_and_aggregate(self):
        """Ordering checks both aggregate's last_recorded_sequence and history."""
        service, _, history_repo, _ = _make_service()
        cmd1 = _make_command(evaluation_sequence=1)
        service.record_evaluation(cmd1)

        # Verify history tracks the sequence
        last_seq = history_repo.get_last_sequence("family-uuid-001")
        assert last_seq == 1

        cmd2 = _make_command(evaluation_id="eval-002", evaluation_sequence=2)
        result = service.record_evaluation(cmd2)
        assert result.success is True


# --- Tests: Version Transition Handling ---

class TestVersionTransitionHandling:
    """ADR-137: Version boundary tracking."""

    def test_version_id_recorded_in_history(self):
        service, _, history_repo, _ = _make_service()
        cmd = _make_command(capability_version_id="ver-v1")
        service.record_evaluation(cmd)
        history = history_repo.get_by_family("family-uuid-001")
        assert history[0].capability_version_id == "ver-v1"

    def test_version_change_across_evaluations(self):
        service, _, history_repo, _ = _make_service()

        cmd1 = _make_command(evaluation_sequence=1, capability_version_id="ver-v1")
        service.record_evaluation(cmd1)

        cmd2 = _make_command(
            evaluation_id="eval-002",
            evaluation_sequence=2,
            capability_version_id="ver-v2",
        )
        service.record_evaluation(cmd2)

        history = history_repo.get_by_family("family-uuid-001")
        assert len(history) == 2
        assert history[0].capability_version_id == "ver-v1"
        assert history[1].capability_version_id == "ver-v2"

    def test_version_filter_in_history(self):
        """ADR-137: get_by_family_and_version filters by version."""
        service, _, history_repo, _ = _make_service()

        cmd1 = _make_command(evaluation_sequence=1, capability_version_id="ver-v1")
        service.record_evaluation(cmd1)

        cmd2 = _make_command(
            evaluation_id="eval-002",
            evaluation_sequence=2,
            capability_version_id="ver-v2",
        )
        service.record_evaluation(cmd2)

        v1_history = history_repo.get_by_family_and_version("family-uuid-001", "ver-v1")
        v2_history = history_repo.get_by_family_and_version("family-uuid-001", "ver-v2")
        assert len(v1_history) == 1
        assert len(v2_history) == 1


# --- Tests: Governance (ADR-138) ---

class TestGovernance:
    """ADR-138: Consecutive score counters for auto-suspend/unsuspend."""

    def test_low_score_increments_consecutive_counter(self):
        service, health_repo, _, _ = _make_service()
        cmd = _make_command(score=0.2, evaluation_sequence=1)  # below 0.3
        service.record_evaluation(cmd)
        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved.consecutive_low_scores == 1
        assert saved.consecutive_high_scores == 0

    def test_high_score_increments_consecutive_counter(self):
        service, health_repo, _, _ = _make_service()
        cmd = _make_command(score=0.8, evaluation_sequence=1)  # above 0.7
        service.record_evaluation(cmd)
        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved.consecutive_high_scores == 1
        assert saved.consecutive_low_scores == 0

    def test_neutral_score_resets_both_counters(self):
        service, health_repo, _, _ = _make_service()

        # First: low score
        cmd1 = _make_command(score=0.2, evaluation_sequence=1)
        service.record_evaluation(cmd1)

        # Second: neutral score
        cmd2 = _make_command(evaluation_id="eval-002", score=0.5, evaluation_sequence=2)
        service.record_evaluation(cmd2)

        saved = health_repo.get_by_family_id("family-uuid-001")
        assert saved.consecutive_low_scores == 0
        assert saved.consecutive_high_scores == 0

    def test_suspend_event_after_threshold(self):
        """ADR-138: Auto-suspend after 3 consecutive low scores."""
        service, _, _, _ = _make_service()

        all_events = []
        for i in range(SUSPEND_THRESHOLD):
            cmd = _make_command(
                evaluation_id=f"eval-{i:03d}",
                score=0.1,
                evaluation_sequence=i + 1,
            )
            result = service.record_evaluation(cmd)
            all_events.extend(result.events)

        suspend_events = [e for e in all_events if isinstance(e, GovernanceCapabilitySuspendedEvent)]
        assert len(suspend_events) == 1
        assert suspend_events[0].consecutive_low_scores == SUSPEND_THRESHOLD

    def test_unsuspend_event_after_threshold(self):
        """ADR-138: Auto-unsuspend after 2 consecutive high scores."""
        service, _, _, _ = _make_service()

        all_events = []
        for i in range(UNSUSPEND_THRESHOLD):
            cmd = _make_command(
                evaluation_id=f"eval-{i:03d}",
                score=0.9,
                evaluation_sequence=i + 1,
            )
            result = service.record_evaluation(cmd)
            all_events.extend(result.events)

        unsuspend_events = [e for e in all_events if isinstance(e, GovernanceCapabilityUnsuspendedEvent)]
        assert len(unsuspend_events) == 1
        assert unsuspend_events[0].consecutive_high_scores == UNSUSPEND_THRESHOLD


# --- Tests: Transaction Boundary ---

class TestTransactionBoundary:
    """ADR-130: Transaction B must NOT touch evolution records or outbox events
    from Transaction A."""

    def test_service_does_not_accept_evolution_repo(self):
        service, _, _, _ = _make_service()
        assert not hasattr(service, '_evolution_repo')

    def test_service_does_not_accept_version_registry(self):
        service, _, _, _ = _make_service()
        assert not hasattr(service, '_version_registry')
