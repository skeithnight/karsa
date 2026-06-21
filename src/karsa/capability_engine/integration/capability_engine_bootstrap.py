"""CapabilityEngineBootstrap -- Sprint-11. Wave-7 / Sprint-12. Wave-4.

Wires all capability engine dependencies for integration testing.
Uses in-memory repositories by default; can be swapped for Postgres.

Wave-4: Also builds facades and FastAPI app.
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI

from karsa.capability_engine.application.capability_event_dispatcher import (
    CapabilityEventDispatcher,
    SUPPORTED_EVENT_TYPES,
)
from karsa.capability_engine.application.capability_evolution_service import (
    CapabilityEvolutionService,
)
from karsa.capability_engine.application.capability_evolution_replay_service import (
    CapabilityEvolutionReplayService,
)
from karsa.capability_engine.application.capability_evolution_versioning_service import (
    CapabilityEvolutionVersioningService,
)
from karsa.capability_engine.application.capability_projection_service import (
    CapabilityProjectionService,
)
from karsa.capability_engine.application.capability_scoring_service import (
    CapabilityScoringService,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryCapabilityEvolutionRepository,
    InMemoryEvolutionVersionRegistryRepository,
    InMemoryCapabilityHealthScoreRepository,
    InMemoryScoreHistoryRepository,
    InMemoryOutboxRepository,
    InMemoryEvolutionProjectionRepository,
    InMemoryHealthProjectionRepository,
    InMemoryScoreTimeseriesProjectionRepository,
)
from karsa.capability_engine.workers.capability_outbox_worker import (
    CapabilityOutboxWorker,
)
from karsa.capability_engine.workers.capability_projection_worker import (
    CapabilityProjectionWorker,
)
from karsa.capability_engine.application.reconciliation_service import (
    ReconciliationService,
)
from karsa.capability_engine.workers.capability_reconciliation_worker import (
    CapabilityReconciliationWorker,
)
from karsa.capability_engine.workers.capability_dead_letter_worker import (
    CapabilityDeadLetterWorker,
)
from karsa.capability_engine.integration.capability_command_facade import (
    CapabilityCommandFacade,
)
from karsa.capability_engine.integration.capability_query_facade import (
    CapabilityQueryFacade,
)
from karsa.capability_engine.transport.http.dependencies import (
    set_dependencies,
    clear_dependencies,
)
from karsa.capability_engine.transport.http.app import build_fastapi_app as _build_app


@dataclass
class CapabilityEngineContainer:
    """Complete wiring of all capability engine components."""

    # Repositories
    evolution_repo: InMemoryCapabilityEvolutionRepository
    version_registry: InMemoryEvolutionVersionRegistryRepository
    health_score_repo: InMemoryCapabilityHealthScoreRepository
    score_history_repo: InMemoryScoreHistoryRepository
    outbox_repo: InMemoryOutboxRepository
    evolution_projection_repo: InMemoryEvolutionProjectionRepository
    health_projection_repo: InMemoryHealthProjectionRepository
    timeseries_projection_repo: InMemoryScoreTimeseriesProjectionRepository

    # Application services
    evolution_service: CapabilityEvolutionService
    scoring_service: CapabilityScoringService
    replay_service: CapabilityEvolutionReplayService
    versioning_service: CapabilityEvolutionVersioningService
    projection_service: CapabilityProjectionService

    # Workers
    outbox_worker: CapabilityOutboxWorker
    projection_worker: CapabilityProjectionWorker
    reconciliation_worker: CapabilityReconciliationWorker
    reconciliation_service: ReconciliationService
    dead_letter_worker: CapabilityDeadLetterWorker

    # Dispatcher
    dispatcher: CapabilityEventDispatcher

    # Facades (Wave-4)
    command_facade: Optional[CapabilityCommandFacade] = None
    query_facade: Optional[CapabilityQueryFacade] = None


def bootstrap() -> CapabilityEngineContainer:
    """Bootstrap all capability engine components with in-memory repos.

    Returns a fully wired container ready for integration testing.
    """
    # Repositories
    evolution_repo = InMemoryCapabilityEvolutionRepository()
    version_registry = InMemoryEvolutionVersionRegistryRepository()
    health_score_repo = InMemoryCapabilityHealthScoreRepository()
    score_history_repo = InMemoryScoreHistoryRepository()
    outbox_repo = InMemoryOutboxRepository()
    evolution_projection_repo = InMemoryEvolutionProjectionRepository()
    health_projection_repo = InMemoryHealthProjectionRepository()
    timeseries_projection_repo = InMemoryScoreTimeseriesProjectionRepository()

    # Application services
    evolution_service = CapabilityEvolutionService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        outbox_repo=outbox_repo,
    )
    scoring_service = CapabilityScoringService(
        health_score_repo=health_score_repo,
        score_history_repo=score_history_repo,
        outbox_repo=outbox_repo,
    )
    replay_service = CapabilityEvolutionReplayService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        score_history_repo=score_history_repo,
    )
    versioning_service = CapabilityEvolutionVersioningService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        outbox_repo=outbox_repo,
    )
    projection_service = CapabilityProjectionService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        health_score_repo=health_score_repo,
        score_history_repo=score_history_repo,
        evolution_projection_repo=evolution_projection_repo,
        health_projection_repo=health_projection_repo,
        timeseries_projection_repo=timeseries_projection_repo,
    )

    # Dispatcher
    dispatcher = CapabilityEventDispatcher()

    # Workers
    outbox_worker = CapabilityOutboxWorker(
        outbox_repo=outbox_repo,
        dispatcher=dispatcher,
    )
    projection_worker = CapabilityProjectionWorker(
        projection_service=projection_service,
    )
    reconciliation_worker = CapabilityReconciliationWorker(
        evolution_repo=evolution_repo,
        health_score_repo=health_score_repo,
        score_history_repo=score_history_repo,
        projection_service=projection_service,
        scoring_service=scoring_service,
    )
    reconciliation_service = ReconciliationService(
        worker=reconciliation_worker,
    )
    dead_letter_worker = CapabilityDeadLetterWorker(
        outbox_repo=outbox_repo,
        dispatcher=dispatcher,
    )

    # Facades (Wave-4)
    command_facade = CapabilityCommandFacade(
        evolution_service=evolution_service,
        scoring_service=scoring_service,
        projection_service=projection_service,
        reconciliation_service=reconciliation_service,
    )
    query_facade = CapabilityQueryFacade(
        health_projection_repo=health_projection_repo,
        evolution_projection_repo=evolution_projection_repo,
        timeseries_projection_repo=timeseries_projection_repo,
    )

    return CapabilityEngineContainer(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        health_score_repo=health_score_repo,
        score_history_repo=score_history_repo,
        outbox_repo=outbox_repo,
        evolution_projection_repo=evolution_projection_repo,
        health_projection_repo=health_projection_repo,
        timeseries_projection_repo=timeseries_projection_repo,
        evolution_service=evolution_service,
        scoring_service=scoring_service,
        replay_service=replay_service,
        versioning_service=versioning_service,
        projection_service=projection_service,
        outbox_worker=outbox_worker,
        projection_worker=projection_worker,
        reconciliation_worker=reconciliation_worker,
        reconciliation_service=reconciliation_service,
        dead_letter_worker=dead_letter_worker,
        dispatcher=dispatcher,
        command_facade=command_facade,
        query_facade=query_facade,
    )


def build_fastapi_app() -> tuple:
    """Build a fully wired FastAPI app with all dependencies.

    Returns (app, container) tuple.
    Transport layer does not know construction details.
    """
    container = bootstrap()

    # Wire dependency providers
    set_dependencies(
        command_facade=container.command_facade,
        query_facade=container.query_facade,
    )

    # Build FastAPI app (Wave-1 factory)
    app = _build_app()

    return app, container
