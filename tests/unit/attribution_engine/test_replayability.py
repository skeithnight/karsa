"""Replayability tests — Sprint-09."""
import pytest
from datetime import datetime

from karsa.attribution_engine.domain.aggregates.attribution_record import AttributionRecord
from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary
from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality
from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence
from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot


def _make_contribution(dimension="THESIS", bps=30.0):
    return AttributionContribution(
        contribution_id="c1",
        dimension=dimension,
        target_urn="worker-1",
        evidence=AttributionEvidence(source_type="TEST", source_id="eval-1", data_points={}, explanation="test"),
        contribution_bps=bps,
        contribution_pct=bps / 100,
        quality_score=0.7,
        quality_provenance={"source": "SYSTEM_DEFAULT", "score": 0.7},
    )


def _make_record():
    return AttributionRecord(
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
        attribution_summary=AttributionSummary(
            total_variance_bps=50.0,
            thesis_contribution_bps=30.0,
            execution_contribution_bps=10.0,
            allocation_contribution_bps=5.0,
            regime_contribution_bps=3.0,
            residual_bps=2.0,
            interaction_effects_bps=0,
            attribution_confidence=0.7,
            explanation="test",
        ),
        attribution_quality=AttributionQuality(quality_score=0.7, data_completeness=1.0, decomposition_confidence=0.7),
        quality_provenance={"thesis": {"source": "SYSTEM_DEFAULT", "score": 0.7}},
        context_snapshot=AttributionContextSnapshot(evaluation_snapshot={"id": "eval-1"}, decision_snapshot={"id": "dec-1"}, snapshot_hash="abc123"),
        source_request_id="req-1",
        attributed_at=datetime.utcnow(),
        attributed_by="test",
    )


class TestReplayability:
    def test_record_deterministic(self):
        """Same inputs produce identical records."""
        r1 = _make_record()
        r2 = _make_record()
        assert r1.attribution_id == r2.attribution_id
        assert r1.total_variance_bps == r2.total_variance_bps

    def test_contributions_deterministic(self):
        """Same contributions produce identical decomposition."""
        c1 = _make_contribution("THESIS", 30.0)
        c2 = _make_contribution("THESIS", 30.0)
        assert c1.contribution_bps == c2.contribution_bps
        assert c1.dimension == c2.dimension

    def test_summary_deterministic(self):
        """Same summary inputs produce identical output."""
        s1 = AttributionSummary(
            total_variance_bps=50.0,
            thesis_contribution_bps=30.0,
            execution_contribution_bps=10.0,
            allocation_contribution_bps=5.0,
            regime_contribution_bps=3.0,
            residual_bps=2.0,
            interaction_effects_bps=0,
            attribution_confidence=0.7,
            explanation="test",
        )
        s2 = AttributionSummary(
            total_variance_bps=50.0,
            thesis_contribution_bps=30.0,
            execution_contribution_bps=10.0,
            allocation_contribution_bps=5.0,
            regime_contribution_bps=3.0,
            residual_bps=2.0,
            interaction_effects_bps=0,
            attribution_confidence=0.7,
            explanation="test",
        )
        assert s1.total_variance_bps == s2.total_variance_bps
        assert s1.residual_bps == s2.residual_bps

    def test_context_snapshot_immutable(self):
        """Context snapshot cannot be modified after creation."""
        s = AttributionContextSnapshot(
            evaluation_snapshot={"id": "eval-1"},
            decision_snapshot={"id": "dec-1"},
            snapshot_hash="abc123",
        )
        with pytest.raises(AttributeError):
            s.snapshot_hash = "changed"

    def test_contributions_preserved_in_record(self):
        """All contributions are preserved in the record."""
        record = _make_record()
        assert len(record.contributions) == 1
        assert record.contributions[0].dimension == "THESIS"
