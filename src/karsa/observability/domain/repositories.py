
from abc import ABC, abstractmethod
from typing import List, Optional
from .models import TraceSpan, WorkerState, QueueState, MetaHealthLedger, MetricSnapshot

class TraceRepository(ABC):
    @abstractmethod
    def save_span(self, span: TraceSpan) -> None:
        pass
        
    @abstractmethod
    def get_by_trace_id(self, trace_id: str) -> List[TraceSpan]:
        pass

class SnapshotRepository(ABC):
    @abstractmethod
    def upsert_worker_state(self, state: WorkerState) -> None:
        pass
        
    @abstractmethod
    def get_worker_state(self, worker_id: str) -> Optional[WorkerState]:
        pass
        
    @abstractmethod
    def upsert_queue_state(self, state: QueueState) -> None:
        pass
        
    @abstractmethod
    def save_metric(self, metric: MetricSnapshot) -> None:
        pass

class ArchivalRepository(ABC):
    @abstractmethod
    def export_to_cold_storage(self, date_str: str) -> str:
        pass

    @abstractmethod
    def verify_and_fetch_archive(self, s3_uri: str, expected_checksum: str) -> bytes:
        pass
        
    @abstractmethod
    def insert_sandbox_archive(self, raw_bytes: bytes) -> None:
        pass
