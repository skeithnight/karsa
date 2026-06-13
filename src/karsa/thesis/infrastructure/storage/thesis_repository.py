from abc import ABC, abstractmethod
from typing import List, Optional
from karsa.thesis.domain.model.thesis import Thesis
import psycopg
import json
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

class ThesisRepository(ABC):
    @abstractmethod
    def get_by_id(self, thesis_id: str) -> Optional[Thesis]:
        pass
        
    @abstractmethod
    def save(self, thesis: Thesis) -> None:
        pass

class ThesisQueryRepository(ABC):
    @abstractmethod
    def get_active(self) -> List[Thesis]:
        pass
        
    @abstractmethod
    def get_by_state(self, state: str) -> List[Thesis]:
        pass
        
    @abstractmethod
    def get_by_originator(self, originator_id: str) -> List[Thesis]:
        pass

class PostgresThesisRepository(ThesisRepository):
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def get_by_id(self, thesis_id: str) -> Optional[Thesis]:
        from karsa.thesis.infrastructure.storage.thesis_mapper import ThesisMapper
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT thesis_id, state, version, payload, created_at, updated_at FROM thesis WHERE thesis_id = %s",
                (thesis_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ThesisMapper.to_domain(row)

    def save(self, thesis: Thesis) -> None:
        from karsa.thesis.infrastructure.storage.thesis_mapper import ThesisMapper
        payload_dict = ThesisMapper.to_payload(thesis)
        payload_json = json.dumps(payload_dict)
        
        with self.conn.cursor() as cur:
            # Upsert logic depending on whether version == 1 (insert) or > 1 (update)
            if thesis.aggregate_version == 1:
                cur.execute(
                    """
                    INSERT INTO thesis (thesis_id, state, version, payload, created_at, updated_at) 
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (thesis.identity.thesis_id, thesis.state.value, thesis.aggregate_version, payload_json)
                )
            else:
                cur.execute(
                    """
                    UPDATE thesis 
                    SET payload = %s, state = %s, version = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE thesis_id = %s AND version = %s
                    """,
                    (payload_json, thesis.state.value, thesis.aggregate_version, thesis.identity.thesis_id, thesis.aggregate_version - 1)
                )
                if cur.rowcount == 0:
                    raise ConcurrencyConflictError(f"Concurrency conflict saving thesis {thesis.identity.thesis_id}")
