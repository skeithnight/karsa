"""Standard pagination DTO -- Phase-2.

All paginated endpoints must use this contract.
"""

from dataclasses import dataclass
from typing import Any, Dict, Generic, List, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginationMeta:
    """Standard pagination metadata."""

    page: int
    size: int
    total_items: int
    total_pages: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "page": self.page,
            "size": self.size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
        }


@dataclass(frozen=True)
class PaginatedResponse:
    """Standard paginated response envelope.

    All paginated endpoints must return this structure.
    """

    data: List[Any]
    pagination: PaginationMeta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "pagination": self.pagination.to_dict(),
        }
