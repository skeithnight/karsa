from typing import Dict, List, Any

from karsa.allocation.domain.model.value_objects import ProposedWeight, PortfolioContext


class PortfolioContextBuilder:
    """Builds PortfolioContext from current exposure and proposed weights."""

    def build(
        self,
        current_exposure: Dict[str, float],
        proposed_weights: Dict[str, ProposedWeight],
    ) -> PortfolioContext:
        """Builds a PortfolioContext snapshot.

        Args:
            current_exposure: Current portfolio exposure metrics.
                Expected keys: gross_exposure, net_exposure, cash_ratio, concentration.
            proposed_weights: Computed proposed weights from weighting strategy.

        Returns:
            PortfolioContext with current and projected metrics.
        """
        current_gross = current_exposure.get("gross_exposure", 0.0)
        current_net = current_exposure.get("net_exposure", 0.0)
        current_cash = current_exposure.get("cash_ratio", 1.0)
        current_concentration = current_exposure.get("concentration", 0.0)

        # Projected metrics: sum of proposed weights
        total_weight = sum(w.proposed_weight for w in proposed_weights.values())
        projected_gross = total_weight
        projected_net = total_weight
        projected_cash = max(1.0 - total_weight, 0.0)

        # Projected concentration: max single weight
        if proposed_weights.values():
            projected_concentration = max(w.proposed_weight for w in proposed_weights.values())
        else:
            projected_concentration = 0.0

        cash_allocation_pct = max(1.0 - total_weight, 0.0)

        # Concentration impact heuristic
        if len(proposed_weights) >= 5:
            concentration_impact = "LOW"
        elif len(proposed_weights) >= 3:
            concentration_impact = "MEDIUM" if projected_concentration > 0.35 else "LOW"
        else:
            concentration_impact = "HIGH" if projected_concentration > 0.50 else "MEDIUM"

        return PortfolioContext(
            current_gross_exposure=current_gross,
            current_net_exposure=current_net,
            current_cash_ratio=current_cash,
            current_concentration=current_concentration,
            projected_gross_exposure=round(projected_gross, 6),
            projected_net_exposure=round(projected_net, 6),
            projected_cash_ratio=round(projected_cash, 6),
            projected_concentration=round(projected_concentration, 6),
            cash_allocation_pct=round(cash_allocation_pct, 6),
            concentration_impact=concentration_impact,
            alternatives_considered=[
                "Equal weight across all allocatable workers",
                "Top-3 only allocation",
                "Inverse drawdown weighting",
            ],
        )
