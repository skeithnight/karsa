"""RegistryACL -- Sprint-11. Wave-8.

Anti-corruption layer for Version Registry operations.
Translates registry state into public contracts.

Prevents version registry internals from leaking to
external bounded contexts.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from karsa.capability_engine.contracts.capability_evolution_dto import (
    CapabilityEvolutionDTO,
)


class RegistryACL:
    """Translates version registry state into public DTOs.

    ADR-133: Canonical governance via separate registry.
    External contexts see only the canonical evolution summary,
    not the registry mechanics.
    """

    def translate_evolution_to_dto(
        self, evolution_data: Dict[str, Any]
    ) -> CapabilityEvolutionDTO:
        """Translate evolution projection data into public DTO."""
        return CapabilityEvolutionDTO(
            capability_family_id=evolution_data.get(
                "capability_family_id", ""
            ),
            evaluation_id=evolution_data.get("evaluation_id", ""),
            capability_urn=evolution_data.get("capability_urn", ""),
            total_evolutions=evolution_data.get("total_evolutions", 0),
            trigger_type_breakdown=evolution_data.get(
                "trigger_type_breakdown", {}
            ),
            positive_evolutions=evolution_data.get(
                "positive_evolutions", 0
            ),
            negative_evolutions=evolution_data.get(
                "negative_evolutions", 0
            ),
            avg_score_change_bps=evolution_data.get(
                "avg_score_change_bps", 0.0
            ),
            last_score_change_bps=evolution_data.get(
                "last_score_change_bps", 0.0
            ),
            last_evolution_type=evolution_data.get(
                "last_evolution_type", ""
            ),
            last_evaluated_at=evolution_data.get("last_evaluated_at"),
        )

    def translate_registry_entry(
        self,
        entry: Dict[str, Any],
        evolution_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Translate a registry entry into a public-facing dict.

        Strips internal fields (version_id, superseded_by) and
        exposes only what external contexts need.
        """
        result = {
            "capability_family_id": entry.get(
                "capability_family_id", ""
            ),
            "evaluation_id": entry.get("evaluation_id", ""),
            "trigger_type": entry.get("trigger_type", ""),
            "evolution_id": entry.get("evolution_id", ""),
            "evolution_status": entry.get("evolution_status", ""),
        }
        if evolution_data:
            result["evolution_summary"] = evolution_data
        return result
