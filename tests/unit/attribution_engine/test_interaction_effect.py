"""InteractionEffect tests — Sprint-09."""
import pytest

from karsa.attribution_engine.domain.value_objects.interaction_effect import InteractionEffect


class TestInteractionEffect:
    def test_valid_interaction(self):
        ie = InteractionEffect(
            dimension_a="THESIS",
            dimension_b="REGIME",
            shared_effect_bps=5.0,
            explanation="Thesis-regime interaction",
        )
        assert ie.dimension_a == "THESIS"
        assert ie.dimension_b == "REGIME"
        assert ie.shared_effect_bps == 5.0

    def test_frozen(self):
        ie = InteractionEffect(
            dimension_a="THESIS",
            dimension_b="REGIME",
            shared_effect_bps=5.0,
            explanation="test",
        )
        with pytest.raises(AttributeError):
            ie.shared_effect_bps = 10.0
