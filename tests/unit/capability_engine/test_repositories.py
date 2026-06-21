"""Tests for Capability Engine repository layer -- Sprint-11."""

import pytest

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
)
from karsa.capability_engine.domain.value_objects.evolution_delta import (
    EvolutionDelta,
)
from karsa.capability_engine.domain.value_objects.evolution_evidence import (
    EvolutionEvidence,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryCapabilityEvolutionRepository,
    InMemoryCapabilityHealthScoreRepository,
    InMemoryEvolutionVersionRegistryRepository,
    InMemoryOutboxRepository,
    InMemoryScoreHistoryRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    EvolutionVersionRegistryEntry,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    OutboxEvent,
)


# ── Helpers ─────────────────────────────────────────────────────


def _make_evolution(**overrides):
    defaults = dict(
        evolution_id="urn:karsa:capability:evolution:abc123",
        capability_family_id="family-001",
        evaluation_id="eval-001",
        trigger_type="REVIEW_FINDING",
        capability_version_id="ver-001",
        capability_urn="urn:karsa:capability:ns:test:v1",
        evolution_type="SCORE_ADJUSTMENT",
        delta=EvolutionDelta(
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None,
            after_contract_fingerprint=None,
        ),
        evidence=EvolutionEvidence(
            source_type="REVIEW",
            source_id="urn:karsa:review:abc",
            finding_ids=["f1"],
        ),
        context_snapshot=EvolutionContextSnapshot(
            capability_snapshot={"urn": "urn:karsa:capability:ns:test:v1"},
            review_snapshot={"review_id": "rev-1"},
        ),
        evaluation_sequence=1,
    )
    defaults.update(overrides)
    return CapabilityEvolution(**defaults)


def _make_health_score(**overrides):
    defaults = dict(
        health_score_id="health-001",
        capability_family_id="family-001",
        current_score=0.5,
        evaluation_count=0,
        aggregate_version=1,
    )
    defaults.update(overrides)
    return CapabilityHealthScore(**defaults)


# ── Evolution Repository ───────────────────────────────────────


class TestCapabilityEvolutionRepository:
    def test_save_and_load(self):
        repo = InMemoryCapabilityEvolutionRepository()
        record = _make_evolution()
        assert repo.save(record) is True
        loaded = repo.get_by_id("urn:karsa:capability:evolution:abc123")
        assert loaded is not None
        assert loaded.evolution_id == record.evolution_id

    def test_duplicate_protection(self):
        repo = InMemoryCapabilityEvolutionRepository()
        r1 = _make_evolution()
        r2 = _make_evolution()  # same identity
        assert repo.save(r1) is True
        assert repo.save(r2) is False  # duplicate

    def test_get_by_family_and_evaluation(self):
        repo = InMemoryCapabilityEvolutionRepository()
        repo.save(_make_evolution(
            evolution_id="urn:karsa:capability:evolution:r1",
            trigger_type="REVIEW_FINDING",
        ))
        repo.save(_make_evolution(
            evolution_id="urn:karsa:capability:evolution:r2",
            trigger_type="ATTRIBUTION_INSIGHT",
            evidence=EvolutionEvidence(
                source_type="ATTRIBUTION",
                source_id="urn:karsa:attribution:abc",
                attribution_contribution_ids=["c1"],
            ),
        ))
        results = repo.get_by_family_and_evaluation("family-001", "eval-001")
        assert len(results) == 2

    def test_get_by_family_evaluation_and_trigger(self):
        repo = InMemoryCapabilityEvolutionRepository()
        repo.save(_make_evolution(
            evolution_id="urn:karsa:capability:evolution:r1",
            trigger_type="REVIEW_FINDING",
        ))
        repo.save(_make_evolution(
            evolution_id="urn:karsa:capability:evolution:r2",
            trigger_type="ATTRIBUTION_INSIGHT",
            evidence=EvolutionEvidence(
                source_type="ATTRIBUTION",
                source_id="urn:karsa:attribution:abc",
                attribution_contribution_ids=["c1"],
            ),
        ))
        found = repo.get_by_family_evaluation_and_trigger(
            "family-001", "eval-001", "ATTRIBUTION_INSIGHT"
        )
        assert found is not None
        assert found.trigger_type == "ATTRIBUTION_INSIGHT"

    def test_list_evolutions_pagination(self):
        repo = InMemoryCapabilityEvolutionRepository()
        for i in range(15):
            repo.save(_make_evolution(
                evolution_id=f"urn:karsa:capability:evolution:{i:03d}",
                evaluation_id=f"eval-{i:03d}",
            ))
        page1 = repo.list_evolutions(page=1, size=10)
        page2 = repo.list_evolutions(page=2, size=10)
        assert len(page1) == 10
        assert len(page2) == 5


# ── Version Registry ───────────────────────────────────────────


class TestEvolutionVersionRegistry:
    def _make_entry(self, **overrides):
        defaults = dict(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="urn:karsa:capability:evolution:abc",
            evolution_status="CANONICAL",
        )
        defaults.update(overrides)
        return EvolutionVersionRegistryEntry(**defaults)

    def test_save_and_get_canonical(self):
        repo = InMemoryEvolutionVersionRegistryRepository()
        entry = self._make_entry()
        repo.save(entry)
        canonical = repo.get_canonical("family-001", "eval-001", "REVIEW_FINDING")
        assert canonical is not None
        assert canonical.evolution_status == "CANONICAL"

    def test_supersede_previous(self):
        repo = InMemoryEvolutionVersionRegistryRepository()
        repo.save(self._make_entry(evolution_id="old-ev"))
        canonical_before = repo.get_canonical(
            "family-001", "eval-001", "REVIEW_FINDING"
        )
        assert canonical_before is not None
        assert canonical_before.evolution_id == "old-ev"
        repo.supersede_previous(
            "family-001", "eval-001", "REVIEW_FINDING", "new-ev"
        )
        canonical_after = repo.get_canonical(
            "family-001", "eval-001", "REVIEW_FINDING"
        )
        # Old is SUPERSEDED, no new canonical inserted yet
        assert canonical_after is None

    def test_get_by_family_and_evaluation(self):
        repo = InMemoryEvolutionVersionRegistryRepository()
        repo.save(self._make_entry(trigger_type="REVIEW_FINDING"))
        repo.save(self._make_entry(
            version_id="vr-002",
            trigger_type="ATTRIBUTION_INSIGHT",
            evolution_id="urn:karsa:capability:evolution:def",
        ))
        results = repo.get_by_family_and_evaluation("family-001", "eval-001")
        assert len(results) == 2

    def test_list_by_family(self):
        repo = InMemoryEvolutionVersionRegistryRepository()
        repo.save(self._make_entry())
        repo.save(self._make_entry(
            version_id="vr-002", evaluation_id="eval-002"
        ))
        results = repo.list_by_family("family-001")
        assert len(results) == 2


# ── Health Score Repository ────────────────────────────────────


class TestCapabilityHealthScoreRepository:
    def test_save_and_load(self):
        repo = InMemoryCapabilityHealthScoreRepository()
        score = _make_health_score()
        assert repo.save(score) is True
        loaded = repo.get_by_family_id("family-001")
        assert loaded is not None
        assert loaded.current_score == 0.5

    def test_occ_conflict_detection(self):
        repo = InMemoryCapabilityHealthScoreRepository()
        s1 = _make_health_score(aggregate_version=1)
        repo.save(s1)
        # Simulate concurrent update: s1 bumps version
        s1.increment_version()
        repo.save(s1)  # version 2, succeeds
        # Old version should conflict
        s2_stale = _make_health_score(aggregate_version=1)
        assert repo.save(s2_stale) is False

    def test_list_by_score_range(self):
        repo = InMemoryCapabilityHealthScoreRepository()
        repo.save(_make_health_score(current_score=0.3))
        repo.save(_make_health_score(
            capability_family_id="family-002", current_score=0.7
        ))
        repo.save(_make_health_score(
            capability_family_id="family-003", current_score=0.9
        ))
        high = repo.list_by_score_range(0.6, 1.0)
        assert len(high) == 2

    def test_list_all_pagination(self):
        repo = InMemoryCapabilityHealthScoreRepository()
        for i in range(12):
            repo.save(_make_health_score(
                health_score_id=f"hs-{i:03d}",
                capability_family_id=f"family-{i:03d}",
            ))
        page1 = repo.list_all(page=1, size=10)
        assert len(page1) == 10


# ── Score History Repository ───────────────────────────────────


class TestScoreHistoryRepository:
    def test_append_and_load(self):
        repo = InMemoryScoreHistoryRepository()
        entry = ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.75,
            algorithm_version="v1.0",
        )
        assert repo.append(entry) is True
        history = repo.get_by_family("family-001")
        assert len(history) == 1
        assert history[0].score == 0.75

    def test_evaluation_ordering_enforcement(self):
        repo = InMemoryScoreHistoryRepository()
        e1 = ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=5,
            capability_version_id="ver-001",
            score=0.6,
            algorithm_version="v1.0",
        )
        e2 = ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-002",
            evaluation_sequence=3,  # less than 5
            capability_version_id="ver-001",
            score=0.7,
            algorithm_version="v1.0",
        )
        repo.append(e1)
        assert repo.append(e2) is False  # out of order

    def test_get_last_sequence(self):
        repo = InMemoryScoreHistoryRepository()
        repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=5,
            capability_version_id="ver-001",
            score=0.6,
            algorithm_version="v1.0",
        ))
        repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-002",
            evaluation_sequence=10,
            capability_version_id="ver-001",
            score=0.7,
            algorithm_version="v1.0",
        ))
        assert repo.get_last_sequence("family-001") == 10

    def test_get_by_family_and_version(self):
        repo = InMemoryScoreHistoryRepository()
        repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-001",
            evaluation_sequence=1,
            capability_version_id="ver-001",
            score=0.6,
            algorithm_version="v1.0",
        ))
        repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="eval-002",
            evaluation_sequence=2,
            capability_version_id="ver-002",
            score=0.7,
            algorithm_version="v1.0",
        ))
        v1_history = repo.get_by_family_and_version("family-001", "ver-001")
        assert len(v1_history) == 1
        assert v1_history[0].capability_version_id == "ver-001"


# ── Outbox Repository ──────────────────────────────────────────


class TestOutboxRepository:
    def _make_event(self, **overrides):
        defaults = dict(
            outbox_id="ob-001",
            event_type="CapabilityEvolutionRecordedEvent",
            payload='{"event_id": "evt-001"}',
            aggregate_id="family-001",
        )
        defaults.update(overrides)
        return OutboxEvent(**defaults)

    def test_save_and_get_pending(self):
        repo = InMemoryOutboxRepository()
        event = self._make_event()
        repo.save_event(event)
        pending = repo.get_pending()
        assert len(pending) == 1
        assert pending[0].status == "PENDING"

    def test_mark_sent(self):
        repo = InMemoryOutboxRepository()
        repo.save_event(self._make_event())
        repo.mark_sent("ob-001")
        pending = repo.get_pending()
        assert len(pending) == 0

    def test_mark_failed(self):
        repo = InMemoryOutboxRepository()
        repo.save_event(self._make_event())
        repo.mark_failed("ob-001")
        pending = repo.get_pending()
        assert len(pending) == 0
        event = repo._store["ob-001"]
        assert event.status == "FAILED"
        assert event.retry_count == 1

    def test_increment_retry(self):
        repo = InMemoryOutboxRepository()
        repo.save_event(self._make_event())
        repo.increment_retry("ob-001")
        event = repo._store["ob-001"]
        assert event.retry_count == 1
        repo.increment_retry("ob-001")
        event = repo._store["ob-001"]
        assert event.retry_count == 2

    def test_get_pending_limit(self):
        repo = InMemoryOutboxRepository()
        for i in range(15):
            repo.save_event(self._make_event(outbox_id=f"ob-{i:03d}"))
        pending = repo.get_pending(limit=5)
        assert len(pending) == 5


# ── ADR Compliance ─────────────────────────────────────────────


class TestADRCompliance:
    def test_adr_120_composite_identity(self):
        """ADR-120: save rejects duplicate (family, eval, trigger)."""
        repo = InMemoryCapabilityEvolutionRepository()
        r1 = _make_evolution(
            evolution_id="urn:karsa:capability:evolution:r1",
            trigger_type="REVIEW_FINDING",
        )
        r2 = _make_evolution(
            evolution_id="urn:karsa:capability:evolution:r2",
            trigger_type="REVIEW_FINDING",
        )  # same trigger
        r3 = _make_evolution(
            evolution_id="urn:karsa:capability:evolution:r3",
            trigger_type="ATTRIBUTION_INSIGHT",
            evidence=EvolutionEvidence(
                source_type="ATTRIBUTION",
                source_id="urn:karsa:attribution:x",
                attribution_contribution_ids=["c1"],
            ),
        )
        assert repo.save(r1) is True
        assert repo.save(r2) is False  # duplicate trigger
        assert repo.save(r3) is True  # different trigger

    def test_adr_133_version_registry_independent(self):
        """ADR-133: Version registry is separate from evolution record."""
        evo_repo = InMemoryCapabilityEvolutionRepository()
        reg_repo = InMemoryEvolutionVersionRegistryRepository()
        evo_repo.save(_make_evolution(
            evolution_id="urn:karsa:capability:evolution:abc",
        ))
        reg_repo.save(EvolutionVersionRegistryEntry(
            version_id="vr-001",
            capability_family_id="family-001",
            evaluation_id="eval-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="urn:karsa:capability:evolution:abc",
            evolution_status="CANONICAL",
        ))
        assert evo_repo.get_by_id("urn:karsa:capability:evolution:abc") is not None
        assert reg_repo.get_canonical(
            "family-001", "eval-001", "REVIEW_FINDING"
        ) is not None

    def test_adr_132_health_score_separate_aggregate(self):
        """ADR-132: Health score is mutable, version-tracked."""
        repo = InMemoryCapabilityHealthScoreRepository()
        score = _make_health_score(aggregate_version=1)
        repo.save(score)
        loaded = repo.get_by_family_id("family-001")
        assert loaded.aggregate_version == 1

    def test_adr_136_evaluation_ordering_enforced(self):
        """ADR-136: Repository rejects out-of-order sequences."""
        repo = InMemoryScoreHistoryRepository()
        repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="e1",
            evaluation_sequence=10,
            capability_version_id="v1",
            score=0.5,
            algorithm_version="v1.0",
        ))
        result = repo.append(ScoreHistoryEntry(
            capability_family_id="family-001",
            evaluation_id="e2",
            evaluation_sequence=5,  # < 10
            capability_version_id="v1",
            score=0.6,
            algorithm_version="v1.0",
        ))
        assert result is False
