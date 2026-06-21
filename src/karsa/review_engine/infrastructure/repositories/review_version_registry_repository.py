"""ReviewVersionRegistryRepository — Sprint-10.

Mutable governance repository for canonical review tracking. ADR-107.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VersionRegistryEntry:
    """Version registry entry. Mutable — status transitions allowed."""
    version_id: str
    evaluation_id: str
    review_type: str
    review_version: str
    review_id: str
    review_status: str  # CANONICAL | SUPERSEDED | EXPERIMENTAL
    superseded_by: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReviewVersionRegistryRepository(ABC):
    """Repository for review version registry.

    Mutable governance table. Canonical review status tracked here.
    ADR-107: Exactly one CANONICAL per (evaluation_id, review_type).
    """

    @abstractmethod
    def save(self, entry: VersionRegistryEntry) -> None:
        """Save a new version registry entry."""
        ...

    @abstractmethod
    def get_canonical(self, evaluation_id: str, review_type: str) -> Optional[VersionRegistryEntry]:
        """Get the canonical review for an evaluation and type. ADR-107."""
        ...

    @abstractmethod
    def get_by_evaluation_and_version(
        self, evaluation_id: str, review_type: str, review_version: str
    ) -> Optional[VersionRegistryEntry]:
        """Get version entry by business identity."""
        ...

    @abstractmethod
    def supersede_previous(self, evaluation_id: str, review_type: str, new_review_id: str) -> None:
        """Mark previous canonical as SUPERSEDED. ADR-107."""
        ...

    @abstractmethod
    def list_by_evaluation(self, evaluation_id: str) -> List[VersionRegistryEntry]:
        """List all version entries for an evaluation."""
        ...
