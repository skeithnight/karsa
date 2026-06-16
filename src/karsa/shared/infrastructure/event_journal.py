import json
import psycopg
from typing import List, Dict, Any, Generator
from datetime import datetime

class EventJournalRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def append_event(self, event_id: str, event_type: str, aggregate_type: str, aggregate_id: str, aggregate_version: int, payload: Dict[str, Any], occurred_at: datetime) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_journal (event_id, event_type, aggregate_type, aggregate_id, aggregate_version, payload, occurred_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING global_sequence
                """,
                (event_id, event_type, aggregate_type, aggregate_id, aggregate_version, json.dumps(payload), occurred_at)
            )
            return cur.fetchone()[0]

    def read_events(self, after_sequence: int = 0, batch_size: int = 100) -> List[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT global_sequence, event_id, event_type, aggregate_type, aggregate_id, aggregate_version, payload, occurred_at
                FROM event_journal
                WHERE global_sequence > %s
                ORDER BY global_sequence ASC
                LIMIT %s
                """,
                (after_sequence, batch_size)
            )
            rows = cur.fetchall()
            events = []
            for row in rows:
                events.append({
                    "global_sequence": row[0],
                    "event_id": row[1],
                    "event_type": row[2],
                    "aggregate_type": row[3],
                    "aggregate_id": row[4],
                    "aggregate_version": row[5],
                    "payload": row[6],
                    "occurred_at": row[7]
                })
            return events

class ProjectionCheckpointRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def lock_checkpoint(self, projection_name: str) -> Dict[str, Any]:
        """Locks the checkpoint row and returns its state. If it doesn't exist, inserts and locks."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT last_processed_sequence, status, updated_at FROM projection_checkpoints WHERE projection_name = %s FOR UPDATE",
                (projection_name,)
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO projection_checkpoints (projection_name, last_processed_sequence, status, updated_at) VALUES (%s, %s, %s, NOW()) RETURNING last_processed_sequence, status, updated_at",
                    (projection_name, 0, 'NOT_STARTED')
                )
                row = cur.fetchone()
            
            return {
                "projection_name": projection_name,
                "last_processed_sequence": row[0],
                "status": row[1],
                "updated_at": row[2]
            }

    def update_checkpoint(self, projection_name: str, sequence: int, status: str = 'RUNNING'):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE projection_checkpoints SET last_processed_sequence = %s, status = %s, updated_at = NOW() WHERE projection_name = %s",
                (sequence, status, projection_name)
            )
