"""Integration: OCC Conflict -- Sprint-11. Wave-7.

Scenario 6: Concurrent updates -> Retry -> Conflict -> Dead-letter.
ADR-132.
"""

import json
import pytest

from karsa.capability_engine.application.capability_scoring_service import (
    CapabilityScoringService,
    ScoringCommand,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    OutboxEvent,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_components,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestOCCConflict:
    """ADR-132: OCC retry and conflict paths."""

    def test_occ_retry_succeeds_on_first_attempt(self, ctx):
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
        assert result.occ_retries == 0

    def test_occ_conflict_triggers_retry(self, ctx):
        """Pre-populate with version mismatch to force OCC conflict."""
        # Save aggregate at version 5
        existing = CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
            aggregate_version=5,
        )
        ctx.health_score_repo.save(existing)

        # Simulate concurrent update: bump to version 6
        concurrent = CapabilityHealthScore(
            health_score_id="int-hs-001",
            capability_family_id="int-family-001",
            current_score=0.55,
            aggregate_version=6,
        )
        ctx.health_score_repo._store["int-family-001"] = concurrent

        # Intercept to keep OCC failing
        original_get = ctx.health_score_repo.get_by_family_id

        def intercepting_get(family_id):
            result = original_get(family_id)
            if result is not None:
                ctx.health_score_repo._store[family_id] = CapabilityHealthScore(
                    health_score_id="int-hs-001",
                    capability_family_id=family_id,
                    current_score=0.55,
                    aggregate_version=result.aggregate_version + 1,
                )
            return result

        ctx.health_score_repo.get_by_family_id = intercepting_get

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

        assert result.success is False
        assert result.occ_retries == 3  # max_occ_retries default

    def test_dead_letter_retry_success(self, ctx):
        """FAILED event retried successfully by dead letter worker."""
        # Register handler
        handled = []
        ctx.dispatcher.register(
            "CapabilityEvolutionRecordedEvent",
            lambda p: handled.append(p),
        )

        # Save a FAILED event
        ctx.outbox_repo.save_event(OutboxEvent(
            outbox_id="int-dl-001",
            event_type="CapabilityEvolutionRecordedEvent",
            payload=json.dumps({"evolution_id": "evo-001"}),
            aggregate_id="int-family-001",
            status="FAILED",
            retry_count=1,
        ))

        result = ctx.dead_letter_worker.run()

        assert result.retried == 1
        assert result.sent == 1
        assert len(handled) == 1

    def test_dead_letter_exhaustion(self, ctx):
        """Event at max retries -> dead-lettered, not retried."""
        ctx.outbox_repo.save_event(OutboxEvent(
            outbox_id="int-dl-002",
            event_type="CapabilityEvolutionRecordedEvent",
            payload=json.dumps({"evolution_id": "evo-002"}),
            aggregate_id="int-family-001",
            status="FAILED",
            retry_count=5,  # at threshold
        ))

        result = ctx.dead_letter_worker.run()

        assert result.dead_lettered == 1
        assert result.retried == 0
