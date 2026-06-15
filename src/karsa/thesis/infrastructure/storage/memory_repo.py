from typing import List, Optional
from karsa.thesis.domain.models import (
    Thesis, ThesisSnapshot, ThesisTransition, 
    ThesisAssumptionIdentity, ThesisAssumptionVersion
)
from karsa.thesis.domain.value_objects import LifecycleState
from karsa.thesis.domain.repository.repositories import (
    ThesisRepository, ThesisSnapshotRepository, ThesisTransitionRepository,
    AssumptionIdentityRepository, AssumptionVersionRepository,
    ConcurrencyDriftError, ImmutableMutationError, LineageCycleError
)

class InMemoryThesisRepository(ThesisRepository):
    def __init__(self):
        self._db = {}

    def save(self, thesis: Thesis) -> None:
        urn = thesis.thesis_urn
        if urn in self._db:
            if self._db[urn].aggregate_version != thesis.aggregate_version - 1:
                raise ConcurrencyDriftError()
        self._db[urn] = thesis

    def get_by_urn(self, urn: str) -> Optional[Thesis]:
        return self._db.get(urn)

    def list_active(self, limit: int, last_urn: Optional[str] = None) -> List[Thesis]:
        active_theses = sorted([t for t in self._db.values() if t.current_status == LifecycleState.ACTIVE], key=lambda t: t.thesis_urn)
        result = []
        for t in active_theses:
            if last_urn and t.thesis_urn <= last_urn:
                continue
            result.append(t)
            if len(result) >= limit:
                break
        return result

class InMemoryThesisSnapshotRepository(ThesisSnapshotRepository):
    def __init__(self):
        self._db = {}

    def save(self, snapshot: ThesisSnapshot) -> None:
        if snapshot.snapshot_urn in self._db:
            raise ImmutableMutationError()
        self._db[snapshot.snapshot_urn] = snapshot

    def get_by_urn(self, urn: str) -> Optional[ThesisSnapshot]:
        return self._db.get(urn)

    def fetch_snapshot_lineage(self, snapshot_urn: str) -> List[ThesisSnapshot]:
        lineage = []
        visited = set()
        current = snapshot_urn
        while current:
            if current in visited:
                raise LineageCycleError()
            visited.add(current)
            snap = self.get_by_urn(current)
            if not snap:
                break
            lineage.append(snap)
            current = snap.supersedes_snapshot_urn
        return lineage

class InMemoryThesisTransitionRepository(ThesisTransitionRepository):
    def __init__(self):
        self._db = {}

    def save(self, transition: ThesisTransition) -> None:
        if transition.transition_urn in self._db:
            raise ImmutableMutationError()
        self._db[transition.transition_urn] = transition

    def get_by_urn(self, urn: str) -> Optional[ThesisTransition]:
        return self._db.get(urn)

    def fetch_transition_lineage(self, transition_urn: str) -> List[ThesisTransition]:
        lineage = []
        visited = set()
        current = transition_urn
        while current:
            if current in visited:
                raise LineageCycleError()
            visited.add(current)
            trans = self.get_by_urn(current)
            if not trans:
                break
            lineage.append(trans)
            current = trans.supersedes_transition_urn
        return lineage

class InMemoryAssumptionIdentityRepository(AssumptionIdentityRepository):
    def __init__(self):
        self._db = {}

    def save(self, identity: ThesisAssumptionIdentity) -> None:
        self._db[identity.assumption_urn] = identity

    def get_by_urn(self, urn: str) -> Optional[ThesisAssumptionIdentity]:
        return self._db.get(urn)

class InMemoryAssumptionVersionRepository(AssumptionVersionRepository):
    def __init__(self):
        self._db = {}

    def save(self, version: ThesisAssumptionVersion) -> None:
        key = f"{version.assumption_urn}_{version.assumption_version}"
        if key in self._db:
            raise ImmutableMutationError()
        self._db[key] = version

    def get_by_urn_and_version(self, urn: str, version: int) -> Optional[ThesisAssumptionVersion]:
        key = f"{urn}_{version}"
        return self._db.get(key)
