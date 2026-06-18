import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import psycopg
from psycopg.rows import dict_row

from karsa.domain.events import DomainEvent

class EventJournalRepository:
    def __init__(self, connection: psycopg.Connection):
        self.connection = connection

    def append(self, event: DomainEvent, stream_version: int) -> None:
        """Append a single event to the event journal.
        
        Note: The event_outbox insert is typically handled by the service layer
        or within a single unit of work to ensure atomicity.
        """
        with self.connection.cursor() as cur:
            # Generate a 32-char hex ID for the id column
            record_id = uuid.uuid4().hex
            
            cur.execute("""
                INSERT INTO event_journal (
                    id, stream_id, stream_version, event_type, payload, occurred_at,
                    aggregate_id, aggregate_type, event_id, schema_version
                ) VALUES (
                    %(id)s, %(stream_id)s, %(stream_version)s, %(event_type)s, %(payload)s, %(occurred_at)s,
                    %(aggregate_id)s, %(aggregate_type)s, %(event_id)s, %(schema_version)s
                )
            """, {
                "id": record_id,
                "stream_id": getattr(event, 'stream_id', 'unknown'),
                "stream_version": stream_version,
                "event_type": event.__class__.__name__,
                "payload": json.dumps(getattr(event, 'to_dict', lambda: event.__dict__)()),
                "occurred_at": getattr(event, 'occurred_at', datetime.now(timezone.utc)),
                "aggregate_id": getattr(event, 'aggregate_id', 'unknown'),
                "aggregate_type": getattr(event, 'aggregate_type', 'Unknown'),
                "event_id": getattr(event, 'event_id', str(uuid.uuid4())),
                "schema_version": getattr(event, 'schema_version', 1)
            })

    def get_current_stream_version(self, stream_id: str) -> int:
        with self.connection.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(stream_version), 0) FROM event_journal WHERE stream_id = %s",
                (stream_id,)
            )
            return cur.fetchone()[0]

    def read_events(self, after_sequence: int, batch_size: int = 100) -> List[Dict[str, Any]]:
        with self.connection.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT sequence_id as global_sequence, event_id, event_type, payload, occurred_at,
                       aggregate_id, aggregate_type, stream_id, stream_version
                FROM event_journal
                WHERE sequence_id > %s
                ORDER BY sequence_id ASC
                LIMIT %s
            """, (after_sequence, batch_size))
            return cur.fetchall()

class ProjectionCheckpointRepository:
    def __init__(self, connection: psycopg.Connection):
        self.connection = connection

    def lock_checkpoint(self, projection_name: str) -> Dict[str, Any]:
        with self.connection.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                INSERT INTO projection_checkpoints (projection_name, last_processed_sequence, status, updated_at)
                VALUES (%s, 0, 'RUNNING', now())
                ON CONFLICT (projection_name) DO UPDATE 
                SET status = 'RUNNING', updated_at = now()
                RETURNING projection_name, last_processed_sequence, status
            """, (projection_name,))
            return cur.fetchone()

    def update_checkpoint(self, projection_name: str, last_sequence: int, status: str = 'RUNNING') -> None:
        with self.connection.cursor() as cur:
            cur.execute("""
                UPDATE projection_checkpoints
                SET last_processed_sequence = %s, status = %s, updated_at = now()
                WHERE projection_name = %s
            """, (last_sequence, status, projection_name))
