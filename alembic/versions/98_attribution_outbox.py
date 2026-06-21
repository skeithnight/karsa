"""sprint09 attribution outbox

Revision ID: 98
Revises: 97
Create Date: 2026-06-20

"""
from alembic import op

revision = '98'
down_revision = '97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attribution outbox — transactional outbox for durable event publishing
    op.execute("""
    CREATE TABLE attribution_outbox (
        outbox_id VARCHAR(64) PRIMARY KEY,
        event_type VARCHAR(128) NOT NULL,
        payload JSONB NOT NULL,
        aggregate_id VARCHAR(256) NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        sent_at TIMESTAMPTZ,
        retry_count INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT chk_outbox_status CHECK (status IN ('PENDING', 'SENT', 'FAILED'))
    );
    """)

    op.execute("COMMENT ON TABLE attribution_outbox IS 'Transactional outbox for durable event publishing. ADR pattern.';")

    op.execute("CREATE INDEX idx_outbox_status ON attribution_outbox(status);")
    op.execute("CREATE INDEX idx_outbox_created ON attribution_outbox(created_at);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS attribution_outbox;")
