"""Application ports -- Sprint-11. Wave-9R. TD-004.

Port interfaces owned by the application layer.
Infrastructure implementations import these ports.
Application services import only from this package.
"""

from karsa.capability_engine.application.ports.capability_evolution_port import (
    CapabilityEvolutionPort,
)
from karsa.capability_engine.application.ports.capability_health_score_port import (
    CapabilityHealthScorePort,
)
from karsa.capability_engine.application.ports.capability_score_history_port import (
    CapabilityScoreHistoryPort,
)
from karsa.capability_engine.application.ports.capability_outbox_port import (
    CapabilityOutboxPort,
    OutboxEvent,
)
from karsa.capability_engine.application.ports.capability_version_registry_port import (
    CapabilityVersionRegistryPort,
    VersionRegistryEntry,
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

__all__ = [
    "CapabilityEvolutionPort",
    "CapabilityHealthScorePort",
    "CapabilityScoreHistoryPort",
    "CapabilityOutboxPort",
    "OutboxEvent",
    "CapabilityVersionRegistryPort",
    "VersionRegistryEntry",
    "CapabilityEvolutionProjectionPort",
    "CapabilityHealthProjectionPort",
    "CapabilityTimeseriesProjectionPort",
]
