"""sprint07 review_cycle_status_projection

Revision ID: 78
Revises: 77
Create Date: 2026-06-20

"""
from alembic import op

revision = '78'
down_revision = '77'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review cycle status projection — derived from lifecycle events
    # Mutable: status updated as cycle progresses
    op.execute("""
    CREATE TABLE review_cycle_status_projection (
        cycle_id VARCHAR(64) PRIMARY KEY,
        status VARCHAR(16) NOT NULL DEFAULT 'CREATED',
        review_id VARCHAR(64),
        executed_at TIMESTAMPTZ,
        event_sequence BIGINT NOT NULL DEFAULT 0
    );
    """)

    op.execute("COMMENT ON TABLE review_cycle_status_projection IS 'Derived projection: tracks review cycle lifecycle status. CREATED→DUE→OVERDUE or EXECUTED.';")
    op.execute("COMMENT ON COLUMN review_cycle_status_projection.event_sequence IS 'For idempotent updates. Only process events with higher sequence.';")

    # Indexes
    op.execute("CREATE INDEX ix_review_cycle_status_status ON review_cycle_status_projection(status);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_cycle_status_projection;")
