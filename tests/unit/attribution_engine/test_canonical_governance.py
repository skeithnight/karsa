"""Canonical governance tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.value_objects.enums import AttributionStatus, QualitySource


class TestAttributionStatus:
    def test_canonical_value(self):
        assert AttributionStatus.CANONICAL == "CANONICAL"

    def test_superseded_value(self):
        assert AttributionStatus.SUPERSEDED == "SUPERSEDED"

    def test_experimental_value(self):
        assert AttributionStatus.EXPERIMENTAL == "EXPERIMENTAL"

    def test_all_values(self):
        assert len(AttributionStatus) == 3


class TestQualitySource:
    def test_system_default(self):
        assert QualitySource.SYSTEM_DEFAULT == "SYSTEM_DEFAULT"

    def test_manual_review(self):
        assert QualitySource.MANUAL_REVIEW == "MANUAL_REVIEW"

    def test_thesis_engine(self):
        assert QualitySource.THESIS_ENGINE == "THESIS_ENGINE"

    def test_execution_engine(self):
        assert QualitySource.EXECUTION_ENGINE == "EXECUTION_ENGINE"

    def test_capital_allocation_engine(self):
        assert QualitySource.CAPITAL_ALLOCATION_ENGINE == "CAPITAL_ALLOCATION_ENGINE"

    def test_all_values(self):
        assert len(QualitySource) == 5
