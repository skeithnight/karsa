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
                    cur.execute(
                        """
                        INSERT INTO event_journal (event_id, event_type, aggregate_type, aggregate_id, aggregate_version, payload, occurred_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            event.event_id,
                            event.__class__.__name__,
                            "Unknown", # Aggregate type is not always accessible on base DomainEvent
                            getattr(event, 'causation_id', getattr(event, 'correlation_id', 'unknown')),
                            1,
                            json.dumps(event.__dict__, default=str),
                            datetime.utcnow()
                        )
                    )
        except Exception as e:
            print(f"Failed to publish event to journal: {e}")
            raise
