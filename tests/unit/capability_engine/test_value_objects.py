"""Tests for Capability Engine value objects -- Sprint-11."""

import pytest

from karsa.capability_engine.domain.value_objects.evolution_delta import (
    EvolutionDelta,
)
from karsa.capability_engine.domain.value_objects.evolution_evidence import (
    EvolutionEvidence,
)
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
    _compute_snapshot_hash,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)


# ── EvolutionDelta ──────────────────────────────────────────────


class TestEvolutionDelta:
    def test_valid_delta(self):
        d = EvolutionDelta(
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint="abc123",
            after_contract_fingerprint="abc123",
        )
        assert d.before_score == 0.5
        assert d.after_score == 0.7
        assert d.score_change_bps == 2000.0

    def test_bps_derivation(self):
        """score_change_bps must equal (after - before) * 10000."""
        d = EvolutionDelta(
            before_score=0.4,
            after_score=0.6,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None,
            after_contract_fingerprint=None,
        )
        assert d.score_change_bps == 2000.0

    def test_bps_mismatch_raises(self):
        with pytest.raises(ValueError, match="score_change_bps must equal"):
            EvolutionDelta(
                before_score=0.4,
                after_score=0.6,
                score_change_bps=1000.0,  # wrong
                before_lifecycle_state="ACTIVE",
                after_lifecycle_state="ACTIVE",
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            )

    def test_before_score_out_of_range(self):
        with pytest.raises(ValueError, match="before_score must be 0.0-1.0"):
            EvolutionDelta(
                before_score=1.5,
                after_score=0.7,
                score_change_bps=-8000.0,
                before_lifecycle_state="ACTIVE",
                after_lifecycle_state="ACTIVE",
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            )

    def test_after_score_out_of_range(self):
        with pytest.raises(ValueError, match="after_score must be 0.0-1.0"):
            EvolutionDelta(
                before_score=0.5,
                after_score=-0.1,
                score_change_bps=-6000.0,
                before_lifecycle_state="ACTIVE",
                after_lifecycle_state="ACTIVE",
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            )

    def test_missing_lifecycle_state(self):
        with pytest.raises(ValueError, match="before_lifecycle_state is required"):
            EvolutionDelta(
                before_score=0.5,
                after_score=0.7,
                score_change_bps=2000.0,
                before_lifecycle_state="",
                after_lifecycle_state="ACTIVE",
                before_contract_fingerprint=None,
                after_contract_fingerprint=None,
            )

    def test_frozen(self):
        d = EvolutionDelta(
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None,
            after_contract_fingerprint=None,
        )
        with pytest.raises(AttributeError):
            d.before_score = 0.9  # type: ignore[misc]


# ── EvolutionEvidence ───────────────────────────────────────────


class TestEvolutionEvidence:
    def test_valid_with_findings(self):
        e = EvolutionEvidence(
            source_type="REVIEW",
            source_id="urn:karsa:review:abc",
            finding_ids=["f1", "f2"],
        )
        assert e.source_type == "REVIEW"
        assert len(e.finding_ids) == 2

    def test_valid_with_attribution(self):
        e = EvolutionEvidence(
            source_type="ATTRIBUTION",
            source_id="urn:karsa:attribution:abc",
            attribution_contribution_ids=["c1"],
        )
        assert len(e.attribution_contribution_ids) == 1

    def test_no_provenance_raises(self):
        with pytest.raises(ValueError, match="At least one of"):
            EvolutionEvidence(
                source_type="REVIEW",
                source_id="urn:karsa:review:abc",
            )

    def test_missing_source_type(self):
        with pytest.raises(ValueError, match="source_type is required"):
            EvolutionEvidence(source_type="", source_id="x", finding_ids=["f1"])

    def test_missing_source_id(self):
        with pytest.raises(ValueError, match="source_id is required"):
            EvolutionEvidence(source_type="REVIEW", source_id="", finding_ids=["f1"])

    def test_frozen(self):
        e = EvolutionEvidence(
            source_type="REVIEW",
            source_id="urn:karsa:review:abc",
            finding_ids=["f1"],
        )
        with pytest.raises(AttributeError):
            e.source_type = "OTHER"  # type: ignore[misc]


# ── EvolutionContextSnapshot ────────────────────────────────────


class TestEvolutionContextSnapshot:
    def _make_snapshot(self, **overrides):
        defaults = {
            "capability_snapshot": {"urn": "urn:karsa:capability:test:v1"},
            "review_snapshot": {"review_id": "rev-1"},
        }
        defaults.update(overrides)
        return EvolutionContextSnapshot(**defaults)

    def test_valid_snapshot(self):
        s = self._make_snapshot()
        assert s.capability_snapshot

    def test_valid_with_all_snapshots(self):
        s = self._make_snapshot(
            attribution_snapshot={"attr_id": "attr-1"},
            execution_snapshot={"exec_id": "exec-1"},
        )
        assert s.attribution_snapshot is not None

    def test_no_upstream_snapshot_raises(self):
        with pytest.raises(ValueError, match="At least one of"):
            EvolutionContextSnapshot(
                capability_snapshot={"urn": "test"},
                review_snapshot=None,
                attribution_snapshot=None,
                execution_snapshot=None,
            )

    def test_missing_capability_snapshot(self):
        with pytest.raises(ValueError, match="capability_snapshot is required"):
            EvolutionContextSnapshot(
                capability_snapshot={},
                review_snapshot={"r": 1},
            )

    def test_hash_verification(self):
        s = self._make_snapshot()
        # Compute hash manually
        data = {
            "capability": s.capability_snapshot,
            "review": s.review_snapshot,
            "attribution": s.attribution_snapshot,
            "execution": s.execution_snapshot,
            "source_versions": s.snapshot_source_versions,
        }
        expected_hash = _compute_snapshot_hash(data)
        # Create snapshot with hash
        s_with_hash = EvolutionContextSnapshot(
            capability_snapshot=s.capability_snapshot,
            review_snapshot=s.review_snapshot,
            snapshot_hash=expected_hash,
        )
        assert s_with_hash.verify_hash()

    def test_hash_mismatch_raises(self):
        with pytest.raises(ValueError, match="snapshot_hash mismatch"):
            EvolutionContextSnapshot(
                capability_snapshot={"urn": "test"},
                review_snapshot={"r": 1},
                snapshot_hash="wrong_hash",
            )

    def test_frozen(self):
        s = self._make_snapshot()
        with pytest.raises(AttributeError):
            s.capability_snapshot = {}  # type: ignore[misc]


# ── CapabilityScoreComponent ────────────────────────────────────


class TestCapabilityScoreComponent:
    def test_valid_component(self):
        c = CapabilityScoreComponent(
            component_name="EXECUTION_QUALITY",
            component_score=0.8,
            weight=0.35,
            evaluation_count=10,
            confidence=0.9,
        )
        assert c.component_score == 0.8

    def test_score_out_of_range(self):
        with pytest.raises(ValueError, match="component_score must be 0.0-1.0"):
            CapabilityScoreComponent(
                component_name="EXECUTION_QUALITY",
                component_score=1.5,
                weight=0.35,
                evaluation_count=10,
                confidence=0.9,
            )

    def test_weight_out_of_range(self):
        with pytest.raises(ValueError, match="weight must be 0.0-1.0"):
            CapabilityScoreComponent(
                component_name="EXECUTION_QUALITY",
                component_score=0.8,
                weight=1.5,
                evaluation_count=10,
                confidence=0.9,
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            CapabilityScoreComponent(
                component_name="EXECUTION_QUALITY",
                component_score=0.8,
                weight=0.35,
                evaluation_count=10,
                confidence=-0.1,
            )

    def test_negative_evaluation_count(self):
        with pytest.raises(ValueError, match="evaluation_count must be >= 0"):
            CapabilityScoreComponent(
                component_name="EXECUTION_QUALITY",
                component_score=0.8,
                weight=0.35,
                evaluation_count=-1,
                confidence=0.9,
            )

    def test_missing_component_name(self):
        with pytest.raises(ValueError, match="component_name is required"):
            CapabilityScoreComponent(
                component_name="",
                component_score=0.8,
                weight=0.35,
                evaluation_count=10,
                confidence=0.9,
            )

    def test_frozen(self):
        c = CapabilityScoreComponent(
            component_name="EXECUTION_QUALITY",
            component_score=0.8,
            weight=0.35,
            evaluation_count=10,
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            c.component_score = 0.9  # type: ignore[misc]


# ── ScoreHistoryEntry ──────────────────────────────────────────


class TestScoreHistoryEntry:
    def test_valid_entry(self):
        e = ScoreHistoryEntry(
            capability_family_id="family-1",
            evaluation_id="eval-1",
            evaluation_sequence=1,
            capability_version_id="ver-1",
            score=0.75,
            algorithm_version="v1.0",
        )
        assert e.score == 0.75

    def test_score_out_of_range(self):
        with pytest.raises(ValueError, match="score must be 0.0-1.0"):
            ScoreHistoryEntry(
                capability_family_id="family-1",
                evaluation_id="eval-1",
                evaluation_sequence=1,
                capability_version_id="ver-1",
                score=2.0,
                algorithm_version="v1.0",
            )

    def test_missing_capability_family_id(self):
        with pytest.raises(ValueError, match="capability_family_id is required"):
            ScoreHistoryEntry(
                capability_family_id="",
                evaluation_id="eval-1",
                evaluation_sequence=1,
                capability_version_id="ver-1",
                score=0.75,
                algorithm_version="v1.0",
            )

    def test_missing_evaluation_id(self):
        with pytest.raises(ValueError, match="evaluation_id is required"):
            ScoreHistoryEntry(
                capability_family_id="family-1",
                evaluation_id="",
                evaluation_sequence=1,
                capability_version_id="ver-1",
                score=0.75,
                algorithm_version="v1.0",
            )

    def test_negative_sequence(self):
        with pytest.raises(ValueError, match="evaluation_sequence must be >= 0"):
            ScoreHistoryEntry(
                capability_family_id="family-1",
                evaluation_id="eval-1",
                evaluation_sequence=-1,
                capability_version_id="ver-1",
                score=0.75,
                algorithm_version="v1.0",
            )

    def test_missing_version_id(self):
        with pytest.raises(ValueError, match="capability_version_id is required"):
            ScoreHistoryEntry(
                capability_family_id="family-1",
                evaluation_id="eval-1",
                evaluation_sequence=1,
                capability_version_id="",
                score=0.75,
                algorithm_version="v1.0",
            )

    def test_missing_algorithm_version(self):
        with pytest.raises(ValueError, match="algorithm_version is required"):
            ScoreHistoryEntry(
                capability_family_id="family-1",
                evaluation_id="eval-1",
                evaluation_sequence=1,
                capability_version_id="ver-1",
                score=0.75,
                algorithm_version="",
            )

    def test_frozen(self):
        e = ScoreHistoryEntry(
            capability_family_id="family-1",
            evaluation_id="eval-1",
            evaluation_sequence=1,
            capability_version_id="ver-1",
            score=0.75,
            algorithm_version="v1.0",
        )
        with pytest.raises(AttributeError):
            e.score = 0.9  # type: ignore[misc]
