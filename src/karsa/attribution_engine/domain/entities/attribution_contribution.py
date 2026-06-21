"""AttributionContribution entity — Sprint-09."""
from dataclasses import dataclass, field
from typing import List

from karsa.attribution_engine.domain.value_objects.attribution_evidence import AttributionEvidence
from karsa.attribution_engine.domain.value_objects.interaction_effect import InteractionEffect


@dataclass(frozen=True)
class AttributionContribution:
    """Child entity of AttributionRecord. ADR-096.

    Stored as JSONB within the parent aggregate.
    Not a separate aggregate — no independent lifecycle.
    """
    contribution_id: str
    dimension: str  # THESIS | EXECUTION | ALLOCATION | REGIME | RESIDUAL
    target_urn: str
    evidence: AttributionEvidence
    contribution_bps: float
    contribution_pct: float
    quality_score: float  # consumed from upstream, ADR-100
    quality_provenance: dict  # ADR-105: {"source": "...", "score": ...}
    interaction_effects: List[InteractionEffect] = field(default_factory=list)
    created_at: str = ""  # ISO format

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        assert self.contribution_id, "contribution_id required"
        assert self.dimension in ('THESIS', 'EXECUTION', 'ALLOCATION', 'REGIME', 'RESIDUAL')
        assert 0.0 <= self.quality_score <= 1.0
        assert "source" in self.quality_provenance, "quality_provenance.source required"
        assert "score" in self.quality_provenance, "quality_provenance.score required"
        assert self.quality_provenance["source"] in (
            'SYSTEM_DEFAULT', 'MANUAL_REVIEW',
            'THESIS_ENGINE', 'EXECUTION_ENGINE', 'CAPITAL_ALLOCATION_ENGINE'
        ), f"Invalid quality_provenance.source: {self.quality_provenance['source']}"
