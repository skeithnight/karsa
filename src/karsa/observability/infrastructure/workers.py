
import time
from ..domain.models import QueueState
from ..domain.repositories import SnapshotRepository, ArchivalRepository

class ProjectionDebouncer:
    # ADR-066: Bounded Batch Debouncing
    def __init__(self, repo: SnapshotRepository, max_events: int = 1000):
        self.repo = repo
        self.max_events = max_events
        self.buffer = []
        
    def add_queue_event(self, queue_name: str, status: str):
        self.buffer.append({"queue_name": queue_name, "status": status})
        if len(self.buffer) >= self.max_events:
            self.flush()
            
    def flush(self):
        aggs = {}
        for event in self.buffer:
            qn = event["queue_name"]
            if qn not in aggs:
                aggs[qn] = 0
            aggs[qn] += 1
            
        for qn, pending in aggs.items():
            self.repo.upsert_queue_state(QueueState(queue_name=qn, pending_count=pending))
            
        self.buffer.clear()

class RehydrationWorker:
    # F-02: Cold Storage Rehydration
    def __init__(self, archival_repo: ArchivalRepository):
        self.archival_repo = archival_repo
        
    def rehydrate(self, s3_uri: str, expected_checksum: str):
        raw_bytes = self.archival_repo.verify_and_fetch_archive(s3_uri, expected_checksum)
        self.archival_repo.insert_sandbox_archive(raw_bytes)
