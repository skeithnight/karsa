"""CreateMemoRequest -- Sprint-13. Wave-1G."""

from typing import Optional

from pydantic import BaseModel, Field


class CreateMemoRequest(BaseModel):
    """Request to create an investment memo."""

    ticker: str = Field(..., min_length=1)
    decision: str = Field(
        ..., min_length=1, description="BUY, HOLD, SELL, or PASS"
    )
    conviction_level: str = Field(
        ..., min_length=1, description="STRONG, MEDIUM, or WEAK"
    )
    conviction_score: float = Field(..., ge=0.0, le=10.0)
    conviction_agreement: int = Field(..., ge=0, le=5)
    thesis: str = Field(..., min_length=50, description="Investment thesis (min 50 chars)")
    entry_price: Optional[float] = Field(default=None, ge=0)
    exit_target: Optional[float] = Field(default=None, ge=0)
    stop_loss: Optional[float] = Field(default=None, ge=0)
    position_size_pct: Optional[float] = Field(
        default=None, gt=0.0, le=100.0
    )
