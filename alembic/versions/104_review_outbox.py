"""sprint10 review outbox

Revision ID: 104
Revises: 103
Create Date: 2026-06-20

"""
from alembic import op

revision = '104'
down_revision = '103'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review outbox — transactional outbox for durable event publishing
    op.execute("""
    CREATE TABLE review_outbox (
        outbox_id VARCHAR(64) PRIMARY KEY,
        event_type VARCHAR(128) NOT NULL,
        payload JSONB NOT NULL,
        aggregate_id VARCHAR(256) NOT NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        sent_at TIMESTAMPTZ,
        retry_count INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT chk_review_outbox_status CHECK (status IN ('PENDING', 'SENT', 'FAILED'))
    );
    """)

    op.execute("COMMENT ON TABLE review_outbox IS 'Transactional outbox for durable event publishing. ADR pattern.';")

    op.execute("CREATE INDEX idx_review_outbox_status ON review_outbox(status);")
    op.execute("CREATE INDEX idx_review_outbox_created ON review_outbox(created_at);")
    op.execute("CREATE INDEX idx_review_outbox_aggregate ON review_outbox(aggregate_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_outbox;")
