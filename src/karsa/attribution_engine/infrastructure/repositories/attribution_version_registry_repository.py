"""AttributionVersionRegistryRepository — Sprint-09.

Mutable governance repository for canonical attribution tracking. ADR-102, ADR-104.
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
    algorithm_version: str
    attribution_id: str
    attribution_status: str  # CANONICAL | SUPERSEDED | EXPERIMENTAL
    superseded_by: Optional[str]
    created_at: datetime
    updated_at: datetime


class AttributionVersionRegistryRepository(ABC):
    """Repository for attribution version registry.

    Mutable governance table. Canonical attribution status tracked here.
    ADR-102: Exactly one CANONICAL per evaluation_id.
    """

    @abstractmethod
    def save(self, entry: VersionRegistryEntry) -> None:
        """Save a new version registry entry."""
        ...

    @abstractmethod
    def get_canonical(self, evaluation_id: str) -> Optional[VersionRegistryEntry]:
        """Get the canonical attribution for an evaluation. ADR-102."""
        ...

    @abstractmethod
    def get_by_evaluation_and_algorithm(
        self, evaluation_id: str, algorithm_version: str
    ) -> Optional[VersionRegistryEntry]:
        """Get version entry by business identity."""
        ...

    @abstractmethod
    def supersede_previous(self, evaluation_id: str, new_algorithm_version: str, new_attribution_id: str) -> None:
        """Mark previous canonical as SUPERSEDED. ADR-102."""
        ...

    @abstractmethod
    def list_by_evaluation(self, evaluation_id: str) -> List[VersionRegistryEntry]:
        """List all version entries for an evaluation."""
        ...
