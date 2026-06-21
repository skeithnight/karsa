"""Tests for Capability Engine aggregates -- Sprint-11."""

import pytest

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.entities.evolution_attribution_ref import (
    EvolutionAttributionRef,
)
from karsa.capability_engine.domain.entities.evolution_finding import (
    EvolutionFinding,
)
from karsa.capability_engine.domain.exceptions import (
    InvalidEvolutionError,
    InvalidHealthScoreError,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
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


def _make_evolution(**overrides):
    """Build a valid CapabilityEvolution for testing."""
    defaults = dict(
        evolution_id="urn:karsa:capability:evolution:abc123",
        capability_family_id="family-uuid-001",
        evaluation_id="eval-uuid-001",
        trigger_type="REVIEW_FINDING",
        capability_version_id="ver-uuid-001",
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


# ── CapabilityEvolution ─────────────────────────────────────────


class TestCapabilityEvolution:
    def test_valid_evolution(self):
        e = _make_evolution()
        assert e.evolution_id == "urn:karsa:capability:evolution:abc123"
        assert e.capability_family_id == "family-uuid-001"
        assert e.trigger_type == "REVIEW_FINDING"

    def test_is_canonical_raises(self):
        e = _make_evolution()
        with pytest.raises(NotImplementedError, match="version registry"):
            _ = e.is_canonical

    def test_immutability(self):
        e = _make_evolution()
        with pytest.raises(AttributeError, match="Cannot set attribute"):
            e.evolution_id = "new-id"  # type: ignore[misc]

    def test_cannot_delete_attribute(self):
        e = _make_evolution()
        with pytest.raises(AttributeError, match="Cannot delete attribute"):
            del e.evolution_id  # type: ignore[misc]

    def test_missing_evolution_id(self):
        with pytest.raises(InvalidEvolutionError, match="evolution_id"):
            _make_evolution(evolution_id="")

    def test_missing_capability_family_id(self):
        with pytest.raises(InvalidEvolutionError, match="capability_family_id"):
            _make_evolution(capability_family_id="")

    def test_missing_evaluation_id(self):
        with pytest.raises(InvalidEvolutionError, match="evaluation_id"):
            _make_evolution(evaluation_id="")

    def test_missing_trigger_type(self):
        with pytest.raises(InvalidEvolutionError, match="trigger_type"):
            _make_evolution(trigger_type="")

    def test_missing_capability_version_id(self):
        with pytest.raises(InvalidEvolutionError, match="capability_version_id"):
            _make_evolution(capability_version_id="")

    def test_missing_capability_urn(self):
        with pytest.raises(InvalidEvolutionError, match="capability_urn"):
            _make_evolution(capability_urn="")

    def test_missing_evolution_type(self):
        with pytest.raises(InvalidEvolutionError, match="evolution_type"):
            _make_evolution(evolution_type="")

    def test_negative_evaluation_sequence(self):
        with pytest.raises(InvalidEvolutionError, match="evaluation_sequence"):
            _make_evolution(evaluation_sequence=-1)

    def test_child_finding_validation(self):
        """Invalid child findings propagate validation error."""
        bad_finding = EvolutionFinding(
            finding_id="",
            finding_type="CONCERN",
            severity="HIGH",
            dimension="THESIS",
            description="test",
        )
        with pytest.raises(ValueError, match="finding_id is required"):
            bad_finding._validate()

    def test_child_attribution_ref_validation(self):
        bad_ref = EvolutionAttributionRef(
            contribution_id="",
            dimension="THESIS",
            contribution_bps=100.0,
            quality_score=0.8,
        )
        with pytest.raises(ValueError, match="contribution_id is required"):
            bad_ref._validate()

    def test_adr_120_composite_identity(self):
        """ADR-120: identity is (family_id, eval_id, trigger_type)."""
        e1 = _make_evolution(trigger_type="REVIEW_FINDING")
        e2 = _make_evolution(trigger_type="ATTRIBUTION_INSIGHT")
        # Same family + eval, different trigger = different identity
        assert e1.capability_family_id == e2.capability_family_id
        assert e1.evaluation_id == e2.evaluation_id
        assert e1.trigger_type != e2.trigger_type

    def test_adr_133_no_canonical_on_aggregate(self):
        """ADR-133: canonical status is NOT stored on this aggregate."""
        e = _make_evolution()
        with pytest.raises(NotImplementedError):
            _ = e.is_canonical

    def test_adr_136_evaluation_sequence_stored(self):
        """ADR-136: evaluation_sequence is a first-class field."""
        e = _make_evolution(evaluation_sequence=42)
        assert e.evaluation_sequence == 42


# ── CapabilityHealthScore ───────────────────────────────────────


class TestCapabilityHealthScore:
    def _make_score(self, **overrides):
        defaults = dict(
            health_score_id="health-001",
            capability_family_id="family-001",
            current_score=0.5,
            evaluation_count=0,
            aggregate_version=1,
        )
        defaults.update(overrides)
        return CapabilityHealthScore(**defaults)

    def test_valid_health_score(self):
        s = self._make_score()
        assert s.current_score == 0.5
        assert s.evaluation_count == 0

    def test_aggregate_id_property(self):
        s = self._make_score()
        assert s.aggregate_id == "family-001"

    def test_missing_health_score_id(self):
        with pytest.raises(InvalidHealthScoreError, match="health_score_id"):
            self._make_score(health_score_id="")

    def test_missing_capability_family_id(self):
        with pytest.raises(
            InvalidHealthScoreError, match="capability_family_id"
        ):
            self._make_score(capability_family_id="")

    def test_score_out_of_range(self):
        with pytest.raises(InvalidHealthScoreError, match="current_score"):
            self._make_score(current_score=1.5)

    def test_negative_evaluation_count(self):
        with pytest.raises(
            InvalidHealthScoreError, match="evaluation_count"
        ):
            self._make_score(evaluation_count=-1)

    def test_negative_consecutive_low(self):
        with pytest.raises(
            InvalidHealthScoreError, match="consecutive_low_scores"
        ):
            self._make_score(consecutive_low_scores=-1)

    def test_negative_consecutive_high(self):
        with pytest.raises(
            InvalidHealthScoreError, match="consecutive_high_scores"
        ):
            self._make_score(consecutive_high_scores=-1)

    def test_record_evaluation_updates_score(self):
        s = self._make_score()
        components = [
            CapabilityScoreComponent(
                component_name="EXECUTION_QUALITY",
                component_score=0.8,
                weight=0.35,
                evaluation_count=1,
                confidence=0.7,
            )
        ]
        s.record_evaluation(
            score=0.75,
            components=components,
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.current_score == 0.75
        assert s.evaluation_count == 1
        assert s.last_recorded_sequence == 1
        assert s.algorithm_version == "v1.0"

    def test_record_evaluation_bumps_version(self):
        s = self._make_score()
        initial_version = s.aggregate_version
        s.record_evaluation(
            score=0.6,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.aggregate_version == initial_version + 1

    def test_adr_136_out_of_order_rejected(self):
        """ADR-136: evaluation_sequence must be monotonically increasing."""
        s = self._make_score()
        s.record_evaluation(
            score=0.6,
            components=[],
            evaluation_sequence=5,
            algorithm_version="v1.0",
        )
        with pytest.raises(InvalidHealthScoreError, match="must be >"):
            s.record_evaluation(
                score=0.7,
                components=[],
                evaluation_sequence=3,  # less than 5
                algorithm_version="v1.0",
            )

    def test_adr_136_same_sequence_rejected(self):
        s = self._make_score()
        s.record_evaluation(
            score=0.6,
            components=[],
            evaluation_sequence=5,
            algorithm_version="v1.0",
        )
        with pytest.raises(InvalidHealthScoreError, match="must be >"):
            s.record_evaluation(
                score=0.7,
                components=[],
                evaluation_sequence=5,  # same as 5
                algorithm_version="v1.0",
            )

    def test_adr_138_low_score_increments_consecutive_low(self):
        """ADR-138: consecutive_low_scores increments on low score."""
        s = self._make_score()
        s.record_evaluation(
            score=0.2,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.consecutive_low_scores == 1
        assert s.consecutive_high_scores == 0

    def test_adr_138_high_score_increments_consecutive_high(self):
        """ADR-138: consecutive_high_scores increments on high score."""
        s = self._make_score()
        s.record_evaluation(
            score=0.8,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.consecutive_high_scores == 1
        assert s.consecutive_low_scores == 0

    def test_adr_138_neutral_resets_counters(self):
        """ADR-138: neutral score resets both counters."""
        s = self._make_score()
        # First: low score
        s.record_evaluation(
            score=0.2,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.consecutive_low_scores == 1
        # Then: neutral score
        s.record_evaluation(
            score=0.5,
            components=[],
            evaluation_sequence=2,
            algorithm_version="v1.0",
        )
        assert s.consecutive_low_scores == 0
        assert s.consecutive_high_scores == 0

    def test_adr_138_low_resets_high_counter(self):
        """ADR-138: low score resets high counter."""
        s = self._make_score()
        s.record_evaluation(
            score=0.8,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.consecutive_high_scores == 1
        s.record_evaluation(
            score=0.2,
            components=[],
            evaluation_sequence=2,
            algorithm_version="v1.0",
        )
        assert s.consecutive_high_scores == 0
        assert s.consecutive_low_scores == 1

    def test_adr_138_high_resets_low_counter(self):
        """ADR-138: high score resets low counter."""
        s = self._make_score()
        s.record_evaluation(
            score=0.2,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v1.0",
        )
        assert s.consecutive_low_scores == 1
        s.record_evaluation(
            score=0.8,
            components=[],
            evaluation_sequence=2,
            algorithm_version="v1.0",
        )
        assert s.consecutive_low_scores == 0
        assert s.consecutive_high_scores == 1

    def test_adr_134_algorithm_version_recorded(self):
        """ADR-134: algorithm_version is tracked on each evaluation."""
        s = self._make_score()
        s.record_evaluation(
            score=0.6,
            components=[],
            evaluation_sequence=1,
            algorithm_version="v2.0",
        )
        assert s.algorithm_version == "v2.0"

    def test_adr_132_separate_aggregate(self):
        """ADR-132: health score is mutable, not write-once."""
        s = self._make_score()
        # Can update current_score directly (mutable aggregate)
        s.current_score = 0.9
        assert s.current_score == 0.9

    def test_record_evaluation_score_out_of_range(self):
        s = self._make_score()
        with pytest.raises(InvalidHealthScoreError, match="score must be"):
            s.record_evaluation(
                score=1.5,
                components=[],
                evaluation_sequence=1,
                algorithm_version="v1.0",
            )
