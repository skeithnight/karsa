import json
from datetime import datetime
from karsa.domain.events import DomainEvent
import psycopg
from psycopg_pool import ConnectionPool

class PostgresEventBus:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.published_events = []

    def publish(self, event: DomainEvent) -> None:
        """Writes domain events directly to the event_journal table within the current transaction."""
        self.published_events.append(event)
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    import uuid as _uuid
                    event_id = getattr(event, 'event_id', str(_uuid.uuid4()))
                    record_id = _uuid.uuid4().hex
                    aggregate_id = getattr(event, 'proposal_id', getattr(event, 'causation_id', getattr(event, 'correlation_id', 'unknown')))
                    # Get next stream version
                    cur.execute(
                        "SELECT COALESCE(MAX(stream_version), 0) + 1 FROM event_journal WHERE stream_id = %s",
                        (f"Allocation-{aggregate_id}",)
                    )
                    next_version = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO event_journal (id, stream_id, stream_version, event_id, event_type, aggregate_type, aggregate_id, payload, occurred_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            record_id,
                            f"Allocation-{aggregate_id}",
                            next_version,
                            event_id,
                            event.__class__.__name__,
                            "Allocation",
                            aggregate_id,
                            json.dumps(event.to_dict() if hasattr(event, 'to_dict') else event.__dict__, default=str),
                            datetime.utcnow()
                        )
                    )
        except Exception as e:
            print(f"Failed to publish event to journal: {e}")
            raise
