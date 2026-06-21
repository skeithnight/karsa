"""CapabilityVersionRegistryPort -- Sprint-11. Wave-9R. TD-004.

Port interface for version registry. ADR-133.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class VersionRegistryEntry:
    """Mutable governance entry for evolution canonical status. ADR-133."""

    version_id: str
    capability_family_id: str
    evaluation_id: str
    trigger_type: str
    evolution_id: str
    evolution_status: str  # CANONICAL, SUPERSEDED, EXPERIMENTAL
    superseded_by: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


class CapabilityVersionRegistryPort(ABC):
    """Mutable governance port for evolution canonical status. ADR-133."""

    @abstractmethod
    def save(self, entry: VersionRegistryEntry) -> None:
        """Insert a new version registry entry."""

    @abstractmethod
    def get_canonical(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[VersionRegistryEntry]:
        """Get the single CANONICAL entry for a (family, eval, trigger)."""

    @abstractmethod
    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[VersionRegistryEntry]:
        """All version entries for a capability family + evaluation."""

    @abstractmethod
    def supersede_previous(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
        new_evolution_id: str,
    ) -> None:
        """Mark previous CANONICAL as SUPERSEDED, insert new CANONICAL."""

    @abstractmethod
    def list_by_family(
        self, capability_family_id: str
    ) -> List[VersionRegistryEntry]:
        """All version entries for a capability family."""
