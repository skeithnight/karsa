import psycopg
from karsa.shared.infrastructure.outbox import OutboxRecord

class PostgresOutboxRepository:
    """Repository for managing outbox records within a transaction."""
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def save(self, record: OutboxRecord):
        """Insert a new record into the outbox table."""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO outbox_records (envelope_id, payload, published_status) VALUES (%s, %s, %s)",
                (record.envelope_id, record.payload, record.published_status)
            )

class OutboxDispatcher:
    """Worker class to poll outbox_records and publish events."""
    def __init__(self, pool, batch_size=10):
        self.pool = pool
        self.batch_size = batch_size

    def setup_schema(self):
        """Create the outbox table if it does not exist."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS outbox_records (
                        envelope_id TEXT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        published_status BOOLEAN DEFAULT false,
                        retry_count INT DEFAULT 0,
                        dead_letter BOOLEAN DEFAULT false,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()

    def dispatch_pending(self, publish_callback) -> int:
        """Find pending records, lock them, publish, and mark done."""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # Find pending records, skipping those locked by other workers
                cur.execute("""
                    SELECT envelope_id, payload, retry_count
                    FROM outbox_records 
                    WHERE published_status = false AND dead_letter = false
                    FOR UPDATE SKIP LOCKED 
                    LIMIT %s
                """, (self.batch_size,))
                
                rows = cur.fetchall()
                if not rows:
                    return 0

                dispatched_ids = []
                failed_ids = []
                dead_letter_ids = []
                
                for envelope_id, payload, retry_count in rows:
                    try:
                        publish_callback(payload)
                        dispatched_ids.append(envelope_id)
                    except Exception:
                        if retry_count >= 3:
                            dead_letter_ids.append(envelope_id)
                        else:
                            failed_ids.append(envelope_id)
                
                if dispatched_ids:
                    cur.execute(
                        "UPDATE outbox_records SET published_status = true WHERE envelope_id = ANY(%s)",
                        (dispatched_ids,)
                    )
                if failed_ids:
                    cur.execute(
                        "UPDATE outbox_records SET retry_count = retry_count + 1 WHERE envelope_id = ANY(%s)",
                        (failed_ids,)
                    )
                if dead_letter_ids:
                    cur.execute(
                        "UPDATE outbox_records SET dead_letter = true WHERE envelope_id = ANY(%s)",
                        (dead_letter_ids,)
                    )
                    
                conn.commit()
                return len(dispatched_ids)
