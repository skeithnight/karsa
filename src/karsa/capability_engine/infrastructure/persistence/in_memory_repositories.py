"""In-memory repository implementations for testing -- Sprint-11."""

import copy
from typing import Dict, List, Optional

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_repository import (
    CapabilityEvolutionRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    CapabilityEvolutionVersionRegistryRepository,
    EvolutionVersionRegistryEntry,
)
from karsa.capability_engine.infrastructure.repositories.capability_health_score_repository import (
    CapabilityHealthScoreRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_score_history_repository import (
    CapabilityScoreHistoryRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_outbox_repository import (
    CapabilityEvolutionOutboxRepository,
    OutboxEvent,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_projection_repository import (
    CapabilityEvolutionProjectionRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_health_projection_repository import (
    CapabilityHealthProjectionRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_score_timeseries_repository import (
    CapabilityScoreTimeseriesProjectionRepository,
)


class InMemoryCapabilityEvolutionRepository(CapabilityEvolutionRepository):
    """In-memory write-once repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, CapabilityEvolution] = {}
        self._business_key: Dict[tuple, str] = {}

    def save(self, record: CapabilityEvolution) -> bool:
        key = (
            record.capability_family_id,
            record.evaluation_id,
            record.trigger_type,
        )
        if key in self._business_key:
            return False
        self._store[record.evolution_id] = record
        self._business_key[key] = record.evolution_id
        return True

    def get_by_id(self, evolution_id: str) -> Optional[CapabilityEvolution]:
        return self._store.get(evolution_id)

    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[CapabilityEvolution]:
        return [
            r
            for r in self._store.values()
            if r.capability_family_id == capability_family_id
            and r.evaluation_id == evaluation_id
        ]

    def get_by_family_evaluation_and_trigger(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[CapabilityEvolution]:
        key = (capability_family_id, evaluation_id, trigger_type)
        eid = self._business_key.get(key)
        return self._store.get(eid) if eid else None

    def list_evolutions(
        self, page: int = 1, size: int = 50
    ) -> List[CapabilityEvolution]:
        items = list(self._store.values())
        start = (page - 1) * size
        return items[start : start + size]


class InMemoryEvolutionVersionRegistryRepository(
    CapabilityEvolutionVersionRegistryRepository
):
    """In-memory version registry for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, EvolutionVersionRegistryEntry] = {}
        self._canonical: Dict[tuple, str] = {}

    def save(self, entry: EvolutionVersionRegistryEntry) -> None:
        self._store[entry.version_id] = entry
        key = (
            entry.capability_family_id,
            entry.evaluation_id,
            entry.trigger_type,
        )
        if entry.evolution_status == "CANONICAL":
            self._canonical[key] = entry.version_id

    def get_canonical(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[EvolutionVersionRegistryEntry]:
        key = (capability_family_id, evaluation_id, trigger_type)
        vid = self._canonical.get(key)
        if not vid:
            return None
        entry = self._store.get(vid)
        if entry and entry.evolution_status == "CANONICAL":
            return entry
        return None

    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[EvolutionVersionRegistryEntry]:
        return [
            e
            for e in self._store.values()
            if e.capability_family_id == capability_family_id
            and e.evaluation_id == evaluation_id
        ]

    def supersede_previous(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
        new_evolution_id: str,
    ) -> None:
        key = (capability_family_id, evaluation_id, trigger_type)
        old_vid = self._canonical.pop(key, None)
        if old_vid and old_vid in self._store:
            old = self._store[old_vid]
            self._store[old_vid] = EvolutionVersionRegistryEntry(
                version_id=old.version_id,
                capability_family_id=old.capability_family_id,
                evaluation_id=old.evaluation_id,
                trigger_type=old.trigger_type,
                evolution_id=old.evolution_id,
                evolution_status="SUPERSEDED",
                superseded_by=new_evolution_id,
                created_at=old.created_at,
            )

    def list_by_family(
        self, capability_family_id: str
    ) -> List[EvolutionVersionRegistryEntry]:
        return [
            e
            for e in self._store.values()
            if e.capability_family_id == capability_family_id
        ]


class InMemoryCapabilityHealthScoreRepository(
    CapabilityHealthScoreRepository
):
    """In-memory health score repository with OCC simulation for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, CapabilityHealthScore] = {}

    def save(self, aggregate: CapabilityHealthScore) -> bool:
        """Upsert with OCC.

        Mirrors Postgres: WHERE aggregate_version = EXCLUDED.aggregate_version - 1.
        The incoming aggregate's version must be exactly 1 greater than
        the stored version (i.e., the aggregate was loaded at version N,
        incremented to N+1 by the domain, and is now being saved).

        Stores a deep copy to prevent mutation leakage across calls.
        """
        existing = self._store.get(aggregate.capability_family_id)
        if existing:
            # OCC: incoming must be exactly one version ahead of stored
            if aggregate.aggregate_version != existing.aggregate_version + 1:
                return False
        self._store[aggregate.capability_family_id] = copy.deepcopy(aggregate)
        return True

    def get_by_family_id(
        self, capability_family_id: str
    ) -> Optional[CapabilityHealthScore]:
        stored = self._store.get(capability_family_id)
        return copy.deepcopy(stored) if stored is not None else None

    def list_by_score_range(
        self, min_score: float, max_score: float
    ) -> List[CapabilityHealthScore]:
        return [
            s
            for s in self._store.values()
            if min_score <= s.current_score <= max_score
        ]

    def list_all(
        self, page: int = 1, size: int = 50
    ) -> List[CapabilityHealthScore]:
        items = list(self._store.values())
        start = (page - 1) * size
        return items[start : start + size]


class InMemoryScoreHistoryRepository(CapabilityScoreHistoryRepository):
    """In-memory score history repository for testing."""

    def __init__(self) -> None:
        self._store: List[ScoreHistoryEntry] = []

    def append(self, entry: ScoreHistoryEntry) -> bool:
        # Check ordering
        existing = [
            e
            for e in self._store
            if e.capability_family_id == entry.capability_family_id
        ]
        if existing:
            max_seq = max(e.evaluation_sequence for e in existing)
            if entry.evaluation_sequence <= max_seq:
                return False
        self._store.append(entry)
        return True

    def get_by_family(
        self, capability_family_id: str
    ) -> List[ScoreHistoryEntry]:
        return sorted(
            [
                e
                for e in self._store
                if e.capability_family_id == capability_family_id
            ],
            key=lambda e: e.evaluation_sequence,
        )

    def get_last_sequence(self, capability_family_id: str) -> int:
        entries = self.get_by_family(capability_family_id)
        return max((e.evaluation_sequence for e in entries), default=0)

    def get_by_family_and_version(
        self, capability_family_id: str, capability_version_id: str
    ) -> List[ScoreHistoryEntry]:
        return sorted(
            [
                e
                for e in self._store
                if e.capability_family_id == capability_family_id
                and e.capability_version_id == capability_version_id
            ],
            key=lambda e: e.evaluation_sequence,
        )


class InMemoryOutboxRepository(CapabilityEvolutionOutboxRepository):
    """In-memory outbox repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, OutboxEvent] = {}

    def save_event(self, event: OutboxEvent) -> None:
        self._store[event.outbox_id] = event

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        pending = [e for e in self._store.values() if e.status == "PENDING"]
        return pending[:limit]

    def mark_sent(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            from datetime import datetime

            self._store[outbox_id] = OutboxEvent(
                outbox_id=self._store[outbox_id].outbox_id,
                event_type=self._store[outbox_id].event_type,
                payload=self._store[outbox_id].payload,
                aggregate_id=self._store[outbox_id].aggregate_id,
                status="SENT",
                created_at=self._store[outbox_id].created_at,
                sent_at=datetime.utcnow(),
                retry_count=self._store[outbox_id].retry_count,
            )

    def mark_failed(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id] = OutboxEvent(
                outbox_id=self._store[outbox_id].outbox_id,
                event_type=self._store[outbox_id].event_type,
                payload=self._store[outbox_id].payload,
                aggregate_id=self._store[outbox_id].aggregate_id,
                status="FAILED",
                created_at=self._store[outbox_id].created_at,
                retry_count=self._store[outbox_id].retry_count + 1,
            )

    def increment_retry(self, outbox_id: str) -> None:
        if outbox_id in self._store:
            self._store[outbox_id] = OutboxEvent(
                outbox_id=self._store[outbox_id].outbox_id,
                event_type=self._store[outbox_id].event_type,
                payload=self._store[outbox_id].payload,
                aggregate_id=self._store[outbox_id].aggregate_id,
                status=self._store[outbox_id].status,
                created_at=self._store[outbox_id].created_at,
                retry_count=self._store[outbox_id].retry_count + 1,
            )

    def get_failed(self, limit: int = 100) -> List[OutboxEvent]:
        failed = [e for e in self._store.values() if e.status == "FAILED"]
        return failed[:limit]


class InMemoryEvolutionProjectionRepository(
    CapabilityEvolutionProjectionRepository
):
    """In-memory projection repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict] = {}

    def get_evolution_summary(
        self, capability_family_id: str
    ) -> Optional[Dict]:
        return self._store.get(capability_family_id)

    def get_evolution_by_evaluation(
        self, evaluation_id: str
    ) -> List[Dict]:
        return [
            v
            for v in self._store.values()
            if v.get("evaluation_id") == evaluation_id
        ]

    def rebuild_all(self) -> None:
        pass  # no-op for in-memory


class InMemoryHealthProjectionRepository(
    CapabilityHealthProjectionRepository
):
    """In-memory health projection repository for testing."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict] = {}

    def get_health_score(
        self, capability_family_id: str
    ) -> Optional[Dict]:
        return self._store.get(capability_family_id)

    def get_health_scores_above(self, threshold: float) -> List[Dict]:
        return [
            v for v in self._store.values() if v.get("current_score", 0) > threshold
        ]

    def get_health_scores_below(self, threshold: float) -> List[Dict]:
        return [
            v for v in self._store.values() if v.get("current_score", 0) < threshold
        ]

    def rebuild_all(self) -> None:
        pass


class InMemoryScoreTimeseriesProjectionRepository(
    CapabilityScoreTimeseriesProjectionRepository
):
    """In-memory timeseries projection repository for testing."""

    def __init__(self) -> None:
        self._store: List[Dict] = []

    def get_by_family(
        self, capability_family_id: str
    ) -> List[Dict]:
        return sorted(
            [
                e
                for e in self._store
                if e.get("capability_family_id") == capability_family_id
            ],
            key=lambda e: e.get("evaluation_sequence", 0),
        )

    def get_by_family_and_version(
        self, capability_family_id: str, capability_version_id: str
    ) -> List[Dict]:
        return sorted(
            [
                e
                for e in self._store
                if e.get("capability_family_id") == capability_family_id
                and e.get("capability_version_id") == capability_version_id
            ],
            key=lambda e: e.get("evaluation_sequence", 0),
        )

    def rebuild_all(self) -> None:
        pass
