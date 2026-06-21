"""CommandResultResponse -- Sprint-12. Wave-2.

Standardized response for all command endpoints.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CommandResultResponse(BaseModel):
    """Response envelope for command operations."""

    success: bool
    message: str
    request_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracing"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional result data"
    )
