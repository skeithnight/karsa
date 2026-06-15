from abc import ABC, abstractmethod
from typing import Optional, List, Any

from .models import RegimeSession, RegimeSnapshot, RegimeTransition

class ConcurrencyError(Exception):
    pass

class ImmutableUpdateError(Exception):
    pass

class RegimeSessionRepository(ABC):
    @abstractmethod
    def save(self, session: RegimeSession) -> None:
        pass

    @abstractmethod
    def find_by_urn(self, session_urn: str) -> Optional[RegimeSession]:
        pass

    @abstractmethod
    def find_paginated(self, limit: int, last_urn: Optional[str] = None) -> List[RegimeSession]:
        pass

class RegimeSnapshotRepository(ABC):
    @abstractmethod
    def save(self, snapshot: RegimeSnapshot) -> None:
        pass

    @abstractmethod
    def find_by_urn(self, snapshot_urn: str) -> Optional[RegimeSnapshot]:
        pass

    @abstractmethod
    def find_by_natural_key(self, segment_urn: str, horizon_urn: str, snapshot_date: str) -> Optional[RegimeSnapshot]:
        pass

    @abstractmethod
    def find_by_segment_paginated(self, segment_urn: str, limit: int, last_date: Optional[str] = None, last_urn: Optional[str] = None) -> List[RegimeSnapshot]:
        pass

    @abstractmethod
    def find_by_horizon_paginated(self, horizon_urn: str, limit: int, last_date: Optional[str] = None, last_urn: Optional[str] = None) -> List[RegimeSnapshot]:
        pass

    @abstractmethod
    def find_snapshot_lineage(self, start_urn: str) -> List[RegimeSnapshot]:
        pass

class RegimeTransitionRepository(ABC):
    @abstractmethod
    def save(self, transition: RegimeTransition) -> None:
        pass

    @abstractmethod
    def find_by_urn(self, transition_urn: str) -> Optional[RegimeTransition]:
        pass

    @abstractmethod
    def find_transition_lineage(self, start_urn: str) -> List[RegimeTransition]:
        pass
