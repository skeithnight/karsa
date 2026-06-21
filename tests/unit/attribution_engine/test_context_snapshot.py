"""AttributionContextSnapshot tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot


class TestAttributionContextSnapshot:
    def test_valid_snapshot(self):
        s = AttributionContextSnapshot(
            evaluation_snapshot={"id": "eval-1"},
            decision_snapshot={"id": "dec-1"},
            snapshot_hash="abc123",
        )
        s.validate()

    def test_empty_evaluation_snapshot_raises(self):
        with pytest.raises(AssertionError):
            AttributionContextSnapshot(
                evaluation_snapshot={},
                decision_snapshot={"id": "dec-1"},
                snapshot_hash="abc123",
            ).validate()

    def test_empty_decision_snapshot_raises(self):
        with pytest.raises(AssertionError):
            AttributionContextSnapshot(
                evaluation_snapshot={"id": "eval-1"},
                decision_snapshot={},
                snapshot_hash="abc123",
            ).validate()

    def test_empty_hash_raises(self):
        with pytest.raises(AssertionError):
            AttributionContextSnapshot(
                evaluation_snapshot={"id": "eval-1"},
                decision_snapshot={"id": "dec-1"},
                snapshot_hash="",
            ).validate()

    def test_optional_fields(self):
        s = AttributionContextSnapshot(
            evaluation_snapshot={"id": "eval-1"},
            decision_snapshot={"id": "dec-1"},
            snapshot_hash="abc123",
        )
        assert s.journal_snapshot is None
        assert s.regime_snapshot is None

    def test_with_regime_snapshot(self):
        s = AttributionContextSnapshot(
            evaluation_snapshot={"id": "eval-1"},
            decision_snapshot={"id": "dec-1"},
            regime_snapshot={"regime_at_evaluation": "BULL"},
            snapshot_hash="abc123",
        )
        assert s.regime_snapshot["regime_at_evaluation"] == "BULL"
