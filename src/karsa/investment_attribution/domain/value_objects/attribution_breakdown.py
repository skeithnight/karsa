"""AttributionBreakdown value object -- Sprint-18.

Decomposes portfolio return into selection, allocation, beta, residual.
"""

from dataclasses import dataclass

from karsa.investment_attribution.domain.exceptions import InvalidAttributionError


@dataclass(frozen=True)
class AttributionBreakdown:
    """Performance attribution decomposition.

    Total return = selection + allocation + beta + residual

    - Selection: return from stock picking (vs benchmark weights)
    - Allocation: return from position sizing (overweight winners)
    - Beta: return from market exposure (benchmark return * portfolio beta)
    - Residual: unexplained (fees, slippage, timing)
    """

    selection_pct: float  # percentage points
    allocation_pct: float
    beta_pct: float
    residual_pct: float
    total_return_pct: float  # sum of above

    def __post_init__(self) -> None:
        computed = (
            self.selection_pct
            + self.allocation_pct
            + self.beta_pct
            + self.residual_pct
        )
        if abs(computed - self.total_return_pct) > 0.01:
            raise InvalidAttributionError(
                f"Components sum ({computed:.4f}) != total ({self.total_return_pct:.4f})"
            )

    @classmethod
    def compute(
        cls,
        selection_pct: float,
        allocation_pct: float,
        beta_pct: float,
        residual_pct: float,
    ) -> "AttributionBreakdown":
        """Compute attribution breakdown from components."""
        total = selection_pct + allocation_pct + beta_pct + residual_pct
        return cls(
            selection_pct=round(selection_pct, 4),
            allocation_pct=round(allocation_pct, 4),
            beta_pct=round(beta_pct, 4),
            residual_pct=round(residual_pct, 4),
            total_return_pct=round(total, 4),
        )

    @property
    def is_positive_selection(self) -> bool:
        return self.selection_pct > 0

    @property
    def is_positive_allocation(self) -> bool:
        return self.allocation_pct > 0

    @property
    def dominant_dimension(self) -> str:
        """Which dimension contributed most to return."""
        dims = {
            "SELECTION": abs(self.selection_pct),
            "ALLOCATION": abs(self.allocation_pct),
            "BETA": abs(self.beta_pct),
            "RESIDUAL": abs(self.residual_pct),
        }
        return max(dims, key=dims.get)
