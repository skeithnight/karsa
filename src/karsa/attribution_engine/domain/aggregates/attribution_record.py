"""AttributionRecord aggregate — Sprint-09.

Write-once immutable ledger entry. ADR-093, ADR-094, ADR-096, ADR-097.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from karsa.attribution_engine.domain.entities.attribution_contribution import AttributionContribution
from karsa.attribution_engine.domain.value_objects.attribution_summary import AttributionSummary
from karsa.attribution_engine.domain.value_objects.attribution_quality import AttributionQuality
from karsa.attribution_engine.domain.value_objects.attribution_context_snapshot import AttributionContextSnapshot


class ImmutableLedgerEntry:
    """Base class for write-once immutable ledger entries. ADR-093."""
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise AttributeError(f"Cannot modify '{name}' of an immutable ledger entry.")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        raise AttributeError("Cannot delete attribute of an immutable ledger entry.")


@dataclass
class AttributionRecord(ImmutableLedgerEntry):
    """Write-once attribution record. ADR-093.

    Business identity: (evaluation_id, algorithm_version) — ADR-094
    Technical identity: attribution_id

    attribution_status is NOT stored here.
    Canonical governance is handled exclusively by attribution_version_registry — ADR-102.
    """
    attribution_id: str
    evaluation_id: str
    algorithm_version: str
    decision_id: str
    evaluation_horizon_days: int
    target_urn: str
    target_type: str
    total_realized_return_bps: float
    total_expected_return_bps: float
    total_variance_bps: float
    contributions: List[AttributionContribution]
    attribution_summary: AttributionSummary
    attribution_quality: AttributionQuality
    quality_provenance: dict  # ADR-105
    context_snapshot: AttributionContextSnapshot
    source_request_id: str
    attributed_at: datetime
    attributed_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        assert self.attribution_id, "attribution_id required"
        assert self.evaluation_id, "evaluation_id required"
        assert self.algorithm_version, "algorithm_version required"
        assert self.evaluation_horizon_days > 0
        assert self.contributions, "contributions cannot be empty"
        # ADR-095: contributions + residual must equal total_variance
        self.attribution_summary.validate()
        for c in self.contributions:
            c.validate()

    @property
    def is_canonical(self) -> bool:
        """Canonical status is determined by attribution_version_registry, not stored here."""
        raise NotImplementedError(
            "is_canonical must be queried from attribution_version_registry, not AttributionRecord."
        )
