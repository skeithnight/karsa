"""AttributionRecord tests — Sprint-09."""
import pytest
from datetime import datetime

from karsa.attribution_engine.domain.aggregates.attribution_record import AttributionRecord, ImmutableLedgerEntry
from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary
from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence
from karsa.attribution_engine.domain.value_objects.interaction_effect import InteractionEffect
from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot


def _make_contribution(dimension="THESIS", bps=30.0):
    return AttributionContribution(
        contribution_id="c1",
        dimension=dimension,
        target_urn="worker-1",
        evidence=AttributionEvidence(source_type="TEST", source_id="eval-1", data_points={}, explanation="test"),
        contribution_bps=bps,
        contribution_pct=0.3,
        quality_score=0.7,
        quality_provenance={"source": "SYSTEM_DEFAULT", "score": 0.7},
    )


def _make_summary(total=100.0, thesis=30.0, execution=25.0, allocation=20.0, regime=15.0, residual=10.0):
    return AttributionSummary(
        total_variance_bps=total,
        thesis_contribution_bps=thesis,
        execution_contribution_bps=execution,
        allocation_contribution_bps=allocation,
        regime_contribution_bps=regime,
        residual_bps=residual,
        interaction_effects_bps=0,
        attribution_confidence=0.7,
        explanation="test",
    )


def _make_record(**overrides):
    defaults = dict(
        attribution_id="attr-1",
        evaluation_id="eval-1",
        algorithm_version="v1.0",
        decision_id="dec-1",
        evaluation_horizon_days=30,
        target_urn="worker-1",
        target_type="DECISION",
        total_realized_return_bps=100.0,
        total_expected_return_bps=50.0,
        total_variance_bps=50.0,
        contributions=[_make_contribution()],
        attribution_summary=_make_summary(total=50.0, thesis=30.0, execution=10.0, allocation=5.0, regime=3.0, residual=2.0),
        attribution_quality=AttributionQuality(quality_score=0.7, data_completeness=1.0, decomposition_confidence=0.7),
        quality_provenance={"thesis": {"source": "SYSTEM_DEFAULT", "score": 0.7}},
        context_snapshot=AttributionContextSnapshot(evaluation_snapshot={"id": "eval-1"}, decision_snapshot={"id": "dec-1"}, snapshot_hash="abc123"),
        source_request_id="req-1",
        attributed_at=datetime.utcnow(),
        attributed_by="test",
    )
    defaults.update(overrides)
    return AttributionRecord(**defaults)


class TestAttributionRecordImmutability:
    def test_cannot_modify_fields(self):
        record = _make_record()
        with pytest.raises(AttributeError):
            record.attribution_id = "changed"

    def test_cannot_delete_fields(self):
        record = _make_record()
        with pytest.raises(AttributeError):
            del record.attribution_id


class TestAttributionRecordValidation:
    def test_empty_attribution_id_raises(self):
        with pytest.raises(AssertionError):
            _make_record(attribution_id="")

    def test_empty_evaluation_id_raises(self):
        with pytest.raises(AssertionError):
            _make_record(evaluation_id="")

    def test_empty_contributions_raises(self):
        with pytest.raises(AssertionError):
            _make_record(contributions=[])

    def test_invalid_horizon_raises(self):
        with pytest.raises(AssertionError):
            _make_record(evaluation_horizon_days=0)


class TestAttributionRecordIdentity:
    def test_business_identity(self):
        record = _make_record()
        assert record.evaluation_id == "eval-1"
        assert record.algorithm_version == "v1.0"

    def test_technical_identity(self):
        record = _make_record()
        assert record.attribution_id == "attr-1"

    def test_is_canonical_raises(self):
        record = _make_record()
        with pytest.raises(NotImplementedError):
            _make_record().is_canonical
