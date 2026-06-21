"""CommandResultResponse -- Sprint-13. Wave-1G."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class CommandResultResponse(BaseModel):
    """Response envelope for command operations."""

    success: bool
    message: str
    request_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
