"""RealizedReturn value object -- Sprint-15."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from karsa.investment_memo.domain.exceptions import InvalidReturnError


@dataclass(frozen=True)
class RealizedReturn:
    """Captured return when a position is closed.

    Tracks entry → exit → actual performance vs target.
    """

    ticker: str
    entry_date: date
    entry_price: Decimal
    exit_date: date
    exit_price: Decimal
    quantity: int
    realized_pnl: Decimal  # absolute P&L
    realized_return_pct: float  # percentage return
    holding_period_days: int
    target_price: Optional[Decimal] = None
    target_error_pct: Optional[float] = None  # |actual - target| / target
    close_reason: str = "MANUAL"
    closed_at: datetime = datetime.utcnow()

    def __post_init__(self) -> None:
        if not self.ticker:
            raise InvalidReturnError("ticker is required")
        if self.quantity <= 0:
            raise InvalidReturnError(
                f"quantity must be > 0, got {self.quantity}"
            )
        if self.holding_period_days < 0:
            raise InvalidReturnError(
                f"holding_period_days must be >= 0, got {self.holding_period_days}"
            )
        if self.entry_price <= 0:
            raise InvalidReturnError("entry_price must be > 0")
        if self.exit_price <= 0:
            raise InvalidReturnError("exit_price must be > 0")

    @classmethod
    def compute(
        cls,
        ticker: str,
        entry_date: date,
        entry_price: Decimal,
        exit_date: date,
        exit_price: Decimal,
        quantity: int,
        target_price: Optional[Decimal] = None,
        close_reason: str = "MANUAL",
    ) -> "RealizedReturn":
        """Compute realized return from raw trade data."""
        realized_pnl = (exit_price - entry_price) * quantity
        realized_return_pct = float(
            (exit_price - entry_price) / entry_price * 100
        )
        holding_period = (exit_date - entry_date).days

        target_error_pct = None
        if target_price and target_price > 0:
            target_error_pct = float(
                abs(exit_price - target_price) / target_price * 100
            )

        return cls(
            ticker=ticker,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            exit_price=exit_price,
            quantity=quantity,
            realized_pnl=realized_pnl,
            realized_return_pct=round(realized_return_pct, 4),
            holding_period_days=holding_period,
            target_price=target_price,
            target_error_pct=(
                round(target_error_pct, 4)
                if target_error_pct is not None
                else None
            ),
            close_reason=close_reason,
        )
