"""RecordDebateRequest -- Sprint-13. Wave-1G."""

from pydantic import BaseModel, Field


class ConvictionRequest(BaseModel):
    """Conviction score within a debate."""

    level: str = Field(..., min_length=1, description="STRONG, MEDIUM, WEAK")
    numeric_score: float = Field(..., ge=0.0, le=10.0)
    analyst_agreement: int = Field(..., ge=0, le=5)


class RecordDebateRequest(BaseModel):
    """Request to record a debate round."""

    round_number: int = Field(..., ge=1)
    bull_memo: str = Field(..., min_length=50, description="Bull case memo (min 50 chars)")
    bear_memo: str = Field(..., min_length=50, description="Bear case memo (min 50 chars)")
    bull_conviction: ConvictionRequest
    bear_conviction: ConvictionRequest
