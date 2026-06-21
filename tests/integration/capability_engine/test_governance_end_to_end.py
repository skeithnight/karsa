"""Integration: Governance Lifecycle -- Sprint-11. Wave-7.

Scenario 7: Low scores -> Suspended. High scores -> Unsuspended.
ADR-138.
"""

import pytest

from karsa.capability_engine.application.capability_scoring_service import (
    ScoringCommand,
    SUSPEND_THRESHOLD,
    UNSUSPEND_THRESHOLD,
)
from karsa.capability_engine.domain.events.capability_events import (
    GovernanceCapabilitySuspendedEvent,
    GovernanceCapabilityUnsuspendedEvent,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_components,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestGovernanceLifecycle:
    """ADR-138: Consecutive low -> suspend, consecutive high -> unsuspend."""

    def test_suspend_after_threshold(self, ctx):
        """3 consecutive low scores -> GovernanceCapabilitySuspendedEvent."""
        all_events = []
        for i in range(SUSPEND_THRESHOLD):
            cmd = ScoringCommand(
                capability_family_id="int-family-001",
                evaluation_id=f"int-eval-{i+1:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="int-ver-001",
                score=0.20,
                components=make_components(),
                algorithm_version="v1.0",
                capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            )
            result = ctx.scoring_service.record_evaluation(cmd)
            all_events.extend(result.events or [])

        suspend_events = [
            e for e in all_events
            if isinstance(e, GovernanceCapabilitySuspendedEvent)
        ]
        assert len(suspend_events) == 1
        assert suspend_events[0].consecutive_low_scores == SUSPEND_THRESHOLD

        # Verify aggregate state
        hs = ctx.health_score_repo.get_by_family_id("int-family-001")
        assert hs.consecutive_low_scores == SUSPEND_THRESHOLD

    def test_unsuspend_after_threshold(self, ctx):
        """First suspend, then 2 high scores -> GovernanceCapabilityUnsuspendedEvent."""
        all_events = []

        # Suspend first
        for i in range(SUSPEND_THRESHOLD):
            cmd = ScoringCommand(
                capability_family_id="int-family-001",
                evaluation_id=f"int-eval-low-{i+1:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="int-ver-001",
                score=0.20,
                components=make_components(),
                algorithm_version="v1.0",
                capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            )
            result = ctx.scoring_service.record_evaluation(cmd)
            all_events.extend(result.events or [])

        # Now unsuspend with high scores
        for i in range(UNSUSPEND_THRESHOLD):
            cmd = ScoringCommand(
                capability_family_id="int-family-001",
                evaluation_id=f"int-eval-high-{i+1:03d}",
                evaluation_sequence=SUSPEND_THRESHOLD + i + 1,
                capability_version_id="int-ver-001",
                score=0.75,
                components=make_components(),
                algorithm_version="v1.0",
                capability_urn="urn:karsa:capability:ns:int-family-001:v1",
            )
            result = ctx.scoring_service.record_evaluation(cmd)
            all_events.extend(result.events or [])

        unsuspend_events = [
            e for e in all_events
            if isinstance(e, GovernanceCapabilityUnsuspendedEvent)
        ]
        assert len(unsuspend_events) == 1
        assert unsuspend_events[0].consecutive_high_scores == UNSUSPEND_THRESHOLD

    def test_neutral_score_resets_counters(self, ctx):
        # Low score
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            evaluation_sequence=1,
            capability_version_id="int-ver-001",
            score=0.20,
            components=make_components(),
            algorithm_version="v1.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        hs = ctx.health_score_repo.get_by_family_id("int-family-001")
        assert hs.consecutive_low_scores == 1

        # Neutral score resets both
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-002",
            evaluation_sequence=2,
            capability_version_id="int-ver-001",
            score=0.50,
            components=make_components(),
            algorithm_version="v1.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        hs = ctx.health_score_repo.get_by_family_id("int-family-001")
        assert hs.consecutive_low_scores == 0
        assert hs.consecutive_high_scores == 0
