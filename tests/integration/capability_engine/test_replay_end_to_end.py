"""Integration: Replay Verification -- Sprint-11. Wave-7.

Scenario 8: Snapshot hash validation, Stale snapshot detection, Canonical lookup.
ADR-133, ADR-135.
"""

import pytest

from karsa.capability_engine.domain.value_objects.enums import EvolutionStatus
from karsa.capability_engine.integration.capability_engine_bootstrap import bootstrap
from karsa.capability_engine.integration.capability_engine_fixture import (
    make_evolution,
    make_registry_entry,
    make_snapshot,
)


@pytest.fixture
def ctx():
    return bootstrap()


class TestReplayVerification:
    """ADR-135: Deterministic replay via immutable context snapshots."""

    def test_snapshot_hash_valid(self, ctx):
        evo = make_evolution()
        ctx.evolution_repo.save(evo)

        result = ctx.replay_service.verify_replay_determinism(evo.evolution_id)
        assert result.is_deterministic is True
        assert result.snapshot_hash_valid is True
        assert result.source_versions_match is True

    def test_stale_snapshot_detection(self, ctx):
        evo = make_evolution()
        ctx.evolution_repo.save(evo)

        # Source has advanced
        current_versions = {"review_projection": 5}
        result = ctx.replay_service.verify_snapshot_version(
            evo.evolution_id, current_versions
        )
        assert result.is_stale is True
        assert result.stale_sources is not None

    def test_same_versions_not_stale(self, ctx):
        evo = make_evolution()
        ctx.evolution_repo.save(evo)

        current_versions = {"review_projection": 1}
        result = ctx.replay_service.verify_snapshot_version(
            evo.evolution_id, current_versions
        )
        assert result.is_stale is False

    def test_canonical_lookup(self, ctx):
        """ADR-133: Canonical via version registry."""
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        ctx.version_registry.save(make_registry_entry(
            evolution_id=evo.evolution_id,
        ))

        canonical = ctx.replay_service.get_canonical_evolution(
            evo.capability_family_id,
            evo.evaluation_id,
            evo.trigger_type,
        )
        assert canonical is not None
        assert canonical.evolution_id == evo.evolution_id

    def test_canonical_lookup_returns_none_for_superseded(self, ctx):
        evo = make_evolution()
        ctx.evolution_repo.save(evo)
        ctx.version_registry.save(make_registry_entry(
            evolution_id=evo.evolution_id,
            evolution_status="SUPERSEDED",
        ))

        canonical = ctx.replay_service.get_canonical_evolution(
            evo.capability_family_id,
            evo.evaluation_id,
            evo.trigger_type,
        )
        assert canonical is None

    def test_evolution_history_sorted(self, ctx):
        evo1 = make_evolution(evaluation_sequence=3, evaluation_id="int-eval-003")
        evo2 = make_evolution(evaluation_sequence=1, evaluation_id="int-eval-001")
        evo3 = make_evolution(evaluation_sequence=2, evaluation_id="int-eval-002")
        ctx.evolution_repo.save(evo1)
        ctx.evolution_repo.save(evo2)
        ctx.evolution_repo.save(evo3)

        for evo in [evo1, evo2, evo3]:
            ctx.version_registry.save(make_registry_entry(
                evaluation_id=evo.evaluation_id,
                evolution_id=evo.evolution_id,
            ))

        history = ctx.replay_service.get_evolution_history(evo1.capability_family_id)
        assert len(history) == 3
        assert history[0].evaluation_sequence == 1
        assert history[2].evaluation_sequence == 3
