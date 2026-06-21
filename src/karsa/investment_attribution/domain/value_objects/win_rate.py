"""WinRate value object -- Sprint-18."""

from dataclasses import dataclass

from karsa.investment_attribution.domain.exceptions import InvalidAttributionError


@dataclass(frozen=True)
class WinRate:
    """Win rate analysis for a category of decisions."""

    category: str  # WinRateCategory value
    total_decisions: int
    winning_decisions: int
    win_rate_pct: float  # 0.0-100.0
    avg_return_pct: float
    avg_winner_return_pct: float
    avg_loser_return_pct: float

    def __post_init__(self) -> None:
        if self.total_decisions < 0:
            raise InvalidAttributionError("total_decisions must be >= 0")
        if self.winning_decisions < 0:
            raise InvalidAttributionError("winning_decisions must be >= 0")
        if self.winning_decisions > self.total_decisions:
            raise InvalidAttributionError(
                "winning_decisions cannot exceed total_decisions"
            )

    @classmethod
    def compute(
        cls,
        category: str,
        returns: list,
    ) -> "WinRate":
        """Compute win rate from a list of realized returns."""
        if not returns:
            return cls(
                category=category,
                total_decisions=0,
                winning_decisions=0,
                win_rate_pct=0.0,
                avg_return_pct=0.0,
                avg_winner_return_pct=0.0,
                avg_loser_return_pct=0.0,
            )

        total = len(returns)
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r <= 0]

        return cls(
            category=category,
            total_decisions=total,
            winning_decisions=len(winners),
            win_rate_pct=round(len(winners) / total * 100, 2),
            avg_return_pct=round(sum(returns) / total, 4),
            avg_winner_return_pct=(
                round(sum(winners) / len(winners), 4) if winners else 0.0
            ),
            avg_loser_return_pct=(
                round(sum(losers) / len(losers), 4) if losers else 0.0
            ),
        )
