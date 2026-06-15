from abc import ABC, abstractmethod
from typing import List, Optional, Any
from karsa.thesis.domain.models import (
    Thesis, ThesisSnapshot, ThesisTransition, 
    ThesisAssumptionIdentity, ThesisAssumptionVersion
)

class ConcurrencyDriftError(Exception): pass  # pragma: no cover
class ImmutableMutationError(Exception): pass  # pragma: no cover
class LineageCycleError(Exception): pass  # pragma: no cover

class ThesisRepository(ABC):
    @abstractmethod
    def save(self, thesis: Thesis) -> None: pass  # pragma: no cover
    @abstractmethod
    def get_by_urn(self, urn: str) -> Optional[Thesis]: pass  # pragma: no cover
    @abstractmethod
    def list_active(self, limit: int, last_urn: Optional[str] = None) -> List[Thesis]: pass  # pragma: no cover

class ThesisSnapshotRepository(ABC):
    @abstractmethod
    def save(self, snapshot: ThesisSnapshot) -> None: pass  # pragma: no cover
    @abstractmethod
    def get_by_urn(self, urn: str) -> Optional[ThesisSnapshot]: pass  # pragma: no cover
    @abstractmethod
    def fetch_snapshot_lineage(self, snapshot_urn: str) -> List[ThesisSnapshot]: pass  # pragma: no cover

class ThesisTransitionRepository(ABC):
    @abstractmethod
    def save(self, transition: ThesisTransition) -> None: pass  # pragma: no cover
    @abstractmethod
    def get_by_urn(self, urn: str) -> Optional[ThesisTransition]: pass  # pragma: no cover
    @abstractmethod
    def fetch_transition_lineage(self, transition_urn: str) -> List[ThesisTransition]: pass  # pragma: no cover

class AssumptionIdentityRepository(ABC):
    @abstractmethod
    def save(self, identity: ThesisAssumptionIdentity) -> None: pass  # pragma: no cover
    @abstractmethod
    def get_by_urn(self, urn: str) -> Optional[ThesisAssumptionIdentity]: pass  # pragma: no cover

class AssumptionVersionRepository(ABC):
    @abstractmethod
    def save(self, version: ThesisAssumptionVersion) -> None: pass  # pragma: no cover
    @abstractmethod
    def get_by_urn_and_version(self, urn: str, version: int) -> Optional[ThesisAssumptionVersion]: pass  # pragma: no cover
