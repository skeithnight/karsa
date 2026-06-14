from abc import ABC, abstractmethod
from typing import List, Optional
from karsa.observability.domain.models import Span

class SpanRepository(ABC):
    @abstractmethod
    def save(self, span: Span) -> None:
        pass

    @abstractmethod
    def save_batch(self, spans: List[Span]) -> None:
        pass

    @abstractmethod
    def find_by_span_id(self, span_id: str) -> Optional[Span]:
        pass

    @abstractmethod
    def find_by_trace_id(self, trace_id: str) -> List[Span]:
        pass

    @abstractmethod
    def find_by_correlation_key(self, key: str, value: str) -> List[Span]:
        pass

    @abstractmethod
    def prune_older_than_days(self, days: int) -> int:
        pass
