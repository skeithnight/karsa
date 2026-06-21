"""ErrorResponse DTO -- Sprint-12. Wave-1.

Standardized error response for all transport layer errors.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope.

    All transport errors return this structure.
    No stack traces are exposed.
    """

    error_code: str
    message: str
