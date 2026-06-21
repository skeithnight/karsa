"""InteractionEffect value object — Sprint-09."""
from dataclasses import dataclass


@dataclass(frozen=True)
class InteractionEffect:
    """Shared impact between two dimensions. ADR-095."""
    dimension_a: str
    dimension_b: str
    shared_effect_bps: float
    explanation: str
