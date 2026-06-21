"""RecordAnalystRequest -- Sprint-13. Wave-1G."""

from typing import List, Optional

from pydantic import BaseModel, Field


class RecordAnalystRequest(BaseModel):
    """Request to record an analyst output."""

    analyst_type: str = Field(
        ..., min_length=1, description="Analyst type (FUNDAMENTAL, TECHNICAL, etc.)"
    )
    score: float = Field(..., ge=0.0, le=10.0, description="Analyst score 0-10")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence 0-1"
    )
    output_text: str = Field(
        ..., min_length=1, description="Analyst output text"
    )
    tools_used: Optional[List[str]] = Field(
        default=None, description="Tools used by analyst"
    )
    model_version: str = Field(default="", description="LLM model version")
