"""Standard error response DTO -- Phase-2.

All error responses must use this contract.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ErrorResponse:
    """Standard error envelope.

    Fields:
    - error_code: Machine-readable error code (e.g. NOT_FOUND, VALIDATION_ERROR)
    - message: Human-readable error message
    - request_id: Optional correlation ID for tracing
    """

    error_code: str
    message: str
    request_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.request_id:
            d["request_id"] = self.request_id
        return d
