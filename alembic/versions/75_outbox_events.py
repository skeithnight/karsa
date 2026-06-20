"""sprint07 outbox_events

Revision ID: 75
Revises: 74
Create Date: 2026-06-20

"""
from alembic import op

revision = '75'
down_revision = '74'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Outbox events — transactional outbox for durable event publishing
    # Status transitions: PENDING → SENT or PENDING → FAILED
    # No immutability trigger (status transitions expected)
    op.execute("""
    CREATE TABLE outbox_events (
        outbox_id VARCHAR(64) PRIMARY KEY,
        event_type VARCHAR(128) NOT NULL,
        payload JSONB NOT NULL,
        aggregate_id VARCHAR(256) NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMPTZ NOT NULL,
        sent_at TIMESTAMPTZ,
        retry_count INTEGER NOT NULL DEFAULT 0
    );
    """)

    op.execute("COMMENT ON TABLE outbox_events IS 'Transactional outbox for durable event publishing. Events saved within domain transaction, published by OutboxPublisherWorker.';")
    op.execute("COMMENT ON COLUMN outbox_events.status IS 'PENDING, SENT, or FAILED. Transitions: PENDING→SENT (published), PENDING→FAILED (max retries).';")
    op.execute("COMMENT ON COLUMN outbox_events.payload IS 'Complete serialized domain event JSON.';")

    # Indexes
    op.execute("CREATE INDEX ix_outbox_events_status ON outbox_events(status);")
    op.execute("CREATE INDEX ix_outbox_events_created_at ON outbox_events(created_at);")
    op.execute("CREATE INDEX ix_outbox_events_aggregate_id ON outbox_events(aggregate_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS outbox_events;")
