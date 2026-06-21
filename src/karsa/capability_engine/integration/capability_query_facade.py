"""CapabilityQueryFacade -- Sprint-11. Wave-8.

Public query interface for the Capability Engine.
External bounded contexts use this facade to read capability
data without referencing projection repositories or internal types.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from karsa.capability_engine.acl.governance_acl import GovernanceACL
from karsa.capability_engine.acl.registry_acl import RegistryACL
from karsa.capability_engine.contracts.capability_health_dto import (
    CapabilityHealthDTO,
)
from karsa.capability_engine.contracts.capability_evolution_dto import (
    CapabilityEvolutionDTO,
)
from karsa.capability_engine.contracts.capability_timeseries_dto import (
    CapabilityTimeseriesDTO,
    CapabilityTimeseriesEntryDTO,
)
from karsa.capability_engine.contracts.governance_status_dto import (
    GovernanceStatusDTO,
)
from karsa.capability_engine.contracts.get_capability_health import (
    GetCapabilityHealthQuery,
)
from karsa.capability_engine.contracts.get_capability_evolution_history import (
    GetCapabilityEvolutionHistoryQuery,
)
from karsa.capability_engine.contracts.get_capability_score_timeseries import (
    GetCapabilityScoreTimeseriesQuery,
)
from karsa.capability_engine.contracts.get_capability_governance_status import (
    GetCapabilityGovernanceStatusQuery,
)
from karsa.capability_engine.application.ports.capability_evolution_projection_port import (
    CapabilityEvolutionProjectionPort,
)
from karsa.capability_engine.application.ports.capability_health_projection_port import (
    CapabilityHealthProjectionPort,
)
from karsa.capability_engine.application.ports.capability_timeseries_projection_port import (
    CapabilityTimeseriesProjectionPort,
)


class CapabilityQueryFacade:
    """Public query interface for the Capability Engine.

    Returns only contract DTOs. Never exposes projection internals,
    repository types, or domain aggregates.
    """

    def __init__(
        self,
        health_projection_repo: CapabilityHealthProjectionPort,
        evolution_projection_repo: CapabilityEvolutionProjectionPort,
        timeseries_projection_repo: CapabilityTimeseriesProjectionPort,
    ) -> None:
        self._health_repo = health_projection_repo
        self._evolution_repo = evolution_projection_repo
        self._timeseries_repo = timeseries_projection_repo
        self._governance_acl = GovernanceACL()
        self._registry_acl = RegistryACL()

    def get_health(
        self, query: GetCapabilityHealthQuery
    ) -> Optional[CapabilityHealthDTO]:
        """Get capability health state as a public DTO."""
        data = self._health_repo.get_health_score(
            query.capability_family_id
        )
        if data is None:
            return None

        return CapabilityHealthDTO(
            capability_family_id=data.get(
                "capability_family_id", ""
            ),
            capability_urn=data.get("capability_urn", ""),
            current_score=data.get("current_score", 0.5),
            algorithm_version=data.get("algorithm_version", "v1.0"),
            execution_quality_score=data.get(
                "execution_quality_score", 0.0
            ),
            attribution_alignment_score=data.get(
                "attribution_alignment_score", 0.0
            ),
            review_sentiment_score=data.get(
                "review_sentiment_score", 0.0
            ),
            regime_fitness_score=data.get(
                "regime_fitness_score", 0.0
            ),
            evaluation_count=data.get("evaluation_count", 0),
            data_completeness=data.get("data_completeness", 0.0),
            score_trend=data.get("score_trend", "UNKNOWN"),
            lifecycle_state=data.get("lifecycle_state", "ACTIVE"),
            last_evaluated_at=data.get("last_evaluated_at"),
            consecutive_low_scores=data.get(
                "consecutive_low_scores", 0
            ),
            consecutive_high_scores=data.get(
                "consecutive_high_scores", 0
            ),
        )

    def get_evolution_history(
        self, query: GetCapabilityEvolutionHistoryQuery
    ) -> Optional[CapabilityEvolutionDTO]:
        """Get capability evolution summary as a public DTO.

        ADR-133: Only canonical records are exposed.
        """
        data = self._evolution_repo.get_evolution_summary(
            query.capability_family_id
        )
        if data is None:
            return None

        return self._registry_acl.translate_evolution_to_dto(data)

    def get_timeseries(
        self, query: GetCapabilityScoreTimeseriesQuery
    ) -> Optional[CapabilityTimeseriesDTO]:
        """Get capability score time series as a public DTO.

        ADR-137: Version boundaries preserved.
        """
        if query.capability_version_id:
            entries = self._timeseries_repo.get_by_family_and_version(
                query.capability_family_id,
                query.capability_version_id,
            )
        else:
            entries = self._timeseries_repo.get_by_family(
                query.capability_family_id
            )

        if not entries:
            return None

        dto_entries = tuple(
            CapabilityTimeseriesEntryDTO(
                capability_family_id=e.get("capability_family_id", ""),
                capability_version_id=e.get(
                    "capability_version_id", ""
                ),
                evaluation_id=e.get("evaluation_id", ""),
                evaluation_sequence=e.get("evaluation_sequence", 0),
                score=e.get("score", 0.0),
                algorithm_version=e.get("algorithm_version", "v1.0"),
                recorded_at=e.get("recorded_at"),
            )
            for e in entries
        )

        return CapabilityTimeseriesDTO(
            capability_family_id=query.capability_family_id,
            entries=dto_entries,
        )

    def get_governance_status(
        self, query: GetCapabilityGovernanceStatusQuery
    ) -> Optional[GovernanceStatusDTO]:
        """Get capability governance status as a public DTO.

        ADR-138: Suspension/unsuspension state.
        """
        data = self._health_repo.get_health_score(
            query.capability_family_id
        )
        if data is None:
            return None

        return self._governance_acl.translate_from_projection(data)
