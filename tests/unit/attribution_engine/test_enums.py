"""Enum tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.value_objects.enums import AttributionDimension


class TestAttributionDimension:
    def test_thesis(self):
        assert AttributionDimension.THESIS == "THESIS"

    def test_execution(self):
        assert AttributionDimension.EXECUTION == "EXECUTION"

    def test_allocation(self):
        assert AttributionDimension.ALLOCATION == "ALLOCATION"

    def test_regime(self):
        assert AttributionDimension.REGIME == "REGIME"

    def test_residual(self):
        assert AttributionDimension.RESIDUAL == "RESIDUAL"
