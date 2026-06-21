"""CapabilityEvolutionVersionRegistryRepository ABC -- Sprint-11. ADR-133."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class EvolutionVersionRegistryEntry:
    """Mutable governance entry for evolution canonical status.

    ADR-133: Exactly one CANONICAL per
    (capability_family_id, evaluation_id, trigger_type).
    """

    version_id: str
    capability_family_id: str
    evaluation_id: str
    trigger_type: str
    evolution_id: str  # URN of the canonical evolution record
    evolution_status: str  # CANONICAL, SUPERSEDED, EXPERIMENTAL
    superseded_by: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


class CapabilityEvolutionVersionRegistryRepository(ABC):
    """Mutable governance repository for evolution canonical status.

    ADR-133: Canonical governance via separate registry. The evolution
    record is immutable; this registry tracks which record is current.
    """

    @abstractmethod
    def save(self, entry: EvolutionVersionRegistryEntry) -> None:
        """Insert a new version registry entry."""

    @abstractmethod
    def get_canonical(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[EvolutionVersionRegistryEntry]:
        """Get the single CANONICAL entry for a (family, eval, trigger)."""

    @abstractmethod
    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[EvolutionVersionRegistryEntry]:
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
    ) -> List[EvolutionVersionRegistryEntry]:
        """All version entries for a capability family."""
