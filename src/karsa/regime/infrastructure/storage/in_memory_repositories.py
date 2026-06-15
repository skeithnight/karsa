import threading
from typing import Optional, List, Dict
import copy

from src.karsa.regime.domain.models import RegimeSession, RegimeSnapshot, RegimeTransition
from src.karsa.regime.domain.repositories import (
    RegimeSessionRepository, RegimeSnapshotRepository, RegimeTransitionRepository,
    ConcurrencyError, ImmutableUpdateError
)
from src.karsa.regime.domain.lineage import reconstruct_transition_lineage, reconstruct_snapshot_lineage, LineageCycleError

class InMemoryRegimeSessionRepository(RegimeSessionRepository):
    def __init__(self):
        self._store: Dict[str, RegimeSession] = {}
        self._lock = threading.Lock()

    def save(self, session: RegimeSession) -> None:
        with self._lock:
            existing = self._store.get(session.session_urn)
            if existing:
                if session.aggregate_version != existing.aggregate_version + 1 and session.aggregate_version != existing.aggregate_version:
                    raise ConcurrencyError("OCC violation")
            else:
                if session.aggregate_version != 1:
                    raise ConcurrencyError("Initial version must be 1")
            
            self._store[session.session_urn] = copy.deepcopy(session)

    def find_by_urn(self, session_urn: str) -> Optional[RegimeSession]:
        with self._lock:
            val = self._store.get(session_urn)
            return copy.deepcopy(val) if val else None

    def find_paginated(self, limit: int, last_urn: Optional[str] = None) -> List[RegimeSession]:
        with self._lock:
            # Deterministic sorting
            urns = sorted(self._store.keys())
            if last_urn:
                urns = [u for u in urns if u > last_urn]
            return [copy.deepcopy(self._store[u]) for u in urns[:limit]]

class InMemoryRegimeSnapshotRepository(RegimeSnapshotRepository):
    def __init__(self):
        self._store: Dict[str, RegimeSnapshot] = {}
        self._lock = threading.Lock()

    def save(self, snapshot: RegimeSnapshot) -> None:
        with self._lock:
            existing = self._store.get(snapshot.snapshot_urn)
            if existing:
                raise ImmutableUpdateError("RegimeSnapshot is immutable and cannot be updated")
            
            # Check natural key
            for s in self._store.values():
                if s.natural_key == snapshot.natural_key:
                    raise ImmutableUpdateError("Natural key violation")

            self._store[snapshot.snapshot_urn] = copy.deepcopy(snapshot)

    def find_by_urn(self, snapshot_urn: str) -> Optional[RegimeSnapshot]:
        with self._lock:
            val = self._store.get(snapshot_urn)
            return copy.deepcopy(val) if val else None

    def find_by_natural_key(self, segment_urn: str, horizon_urn: str, snapshot_date: str) -> Optional[RegimeSnapshot]:
        with self._lock:
            target_key = (segment_urn, horizon_urn, snapshot_date)
            for s in self._store.values():
                if s.natural_key == target_key:
                    return copy.deepcopy(s)
            return None

    def find_by_segment_paginated(self, segment_urn: str, limit: int, last_date: Optional[str] = None, last_urn: Optional[str] = None) -> List[RegimeSnapshot]:
        with self._lock:
            matches = [s for s in self._store.values() if s.segment_urn == segment_urn]
            matches.sort(key=lambda s: (s.snapshot_date, s.snapshot_urn))
            
            if last_date is not None and last_urn is not None:
                matches = [s for s in matches if (s.snapshot_date, s.snapshot_urn) > (last_date, last_urn)]
                
            return [copy.deepcopy(s) for s in matches[:limit]]

    def find_by_horizon_paginated(self, horizon_urn: str, limit: int, last_date: Optional[str] = None, last_urn: Optional[str] = None) -> List[RegimeSnapshot]:
        with self._lock:
            matches = [s for s in self._store.values() if s.horizon_urn == horizon_urn]
            matches.sort(key=lambda s: (s.snapshot_date, s.snapshot_urn))
            
            if last_date is not None and last_urn is not None:
                matches = [s for s in matches if (s.snapshot_date, s.snapshot_urn) > (last_date, last_urn)]
                
            return [copy.deepcopy(s) for s in matches[:limit]]

    def find_snapshot_lineage(self, start_urn: str) -> List[RegimeSnapshot]:
        with self._lock:
            snaps = list(self._store.values())
            # For simplicity, assuming snapshots don't have explicit pointers in models, 
            # but if they did we'd use reconstruct_snapshot_lineage.
            # Returning dummy for now since model doesn't explicitly define supersedes_snapshot_urn.
            val = self._store.get(start_urn)
            if not val:
                return []
            return [copy.deepcopy(val)]

class InMemoryRegimeTransitionRepository(RegimeTransitionRepository):
    def __init__(self):
        self._store: Dict[str, RegimeTransition] = {}
        self._lock = threading.Lock()

    def save(self, transition: RegimeTransition) -> None:
        with self._lock:
            existing = self._store.get(transition.transition_urn)
            if existing:
                if transition.aggregate_version != existing.aggregate_version + 1 and transition.aggregate_version != existing.aggregate_version:
                    raise ConcurrencyError("OCC violation")
            else:
                if transition.aggregate_version != 1:
                    raise ConcurrencyError("Initial version must be 1")
            
            self._store[transition.transition_urn] = copy.deepcopy(transition)

    def find_by_urn(self, transition_urn: str) -> Optional[RegimeTransition]:
        with self._lock:
            val = self._store.get(transition_urn)
            return copy.deepcopy(val) if val else None

    def find_transition_lineage(self, start_urn: str) -> List[RegimeTransition]:
        with self._lock:
            transitions = list(self._store.values())
            return reconstruct_transition_lineage(transitions, start_urn)
