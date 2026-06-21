"""Integration: Scoring Flow -- Sprint-11. Wave-7.

Scenario 2: Evolution history -> Health score update -> History appended -> Outbox.
ADR-132, ADR-134, ADR-136.
"""

import pytest

from karsa.capability_engine.application.capability_scoring_service import (
    ScoringCommand,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_components,
    make_history_entry,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestScoringFlow:
    """End-to-end: ScoringCommand -> HealthScore + History + Outbox."""

    def test_first_evaluation_creates_health_score(self, ctx):
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            evaluation_sequence=1,
            capability_version_id="int-ver-001",
            score=0.75,
            components=make_components(),
            algorithm_version="v1.0",
        )
        result = ctx.scoring_service.record_evaluation(cmd)

        assert result.success is True
        assert result.new_score == 0.75
        assert result.previous_score == 0.5  # default

        # Health score persisted
        hs = ctx.health_score_repo.get_by_family_id("int-family-001")
        assert hs is not None
        assert hs.current_score == 0.75
        assert hs.evaluation_count == 1

    def test_history_appended(self, ctx):
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            evaluation_sequence=1,
            capability_version_id="int-ver-001",
            score=0.75,
            components=make_components(),
            algorithm_version="v1.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        history = ctx.score_history_repo.get_by_family("int-family-001")
        assert len(history) == 1
        assert history[0].score == 0.75
        assert history[0].evaluation_sequence == 1

    def test_outbox_generated(self, ctx):
        cmd = ScoringCommand(
            capability_family_id="int-family-001",
            evaluation_id="int-eval-001",
            evaluation_sequence=1,
            capability_version_id="int-ver-001",
            score=0.75,
            components=make_components(),
            algorithm_version="v1.0",
        )
        ctx.scoring_service.record_evaluation(cmd)

        pending = ctx.outbox_repo.get_pending()
        assert len(pending) >= 1
        event_types = {e.event_type for e in pending}
        assert "CapabilityHealthScoreUpdatedEvent" in event_types

    def test_sequential_evaluations(self, ctx):
        """ADR-136: Monotonic evaluation ordering."""
        for i, score in enumerate([0.6, 0.7, 0.8]):
            cmd = ScoringCommand(
                capability_family_id="int-family-001",
                evaluation_id=f"int-eval-{i+1:03d}",
                evaluation_sequence=i + 1,
                capability_version_id="int-ver-001",
                score=score,
                components=make_components(),
                algorithm_version="v1.0",
            )
            result = ctx.scoring_service.record_evaluation(cmd)
            assert result.success is True

        hs = ctx.health_score_repo.get_by_family_id("int-family-001")
        assert hs.current_score == 0.8
        assert hs.evaluation_count == 3

        history = ctx.score_history_repo.get_by_family("int-family-001")
        assert len(history) == 3
