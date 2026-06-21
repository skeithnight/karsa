"""ProposeDecisionRequest -- Sprint-13. Wave-1G."""

from pydantic import BaseModel, Field


class ProposeDecisionRequest(BaseModel):
    """Request to propose an investment decision."""

    capability_family_id: str = Field(
        ..., min_length=1, description="Capability family UUID"
    )
    ticker: str = Field(..., min_length=1, description="Stock ticker")
    decision_date: str = Field(
        ..., min_length=1, description="Decision date (ISO)"
    )
    proposed_by: str = Field(default="", description="Proposer identifier")
