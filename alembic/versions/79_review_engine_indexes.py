"""sprint07 review engine composite indexes

Revision ID: 79
Revises: 78
Create Date: 2026-06-20

"""
from alembic import op

revision = '79'
down_revision = '78'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite indexes for common query patterns — skip if tables don't exist
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'attribution_entries') THEN
            CREATE INDEX IF NOT EXISTS ix_attribution_entries_review_dimension ON attribution_entries(review_id, dimension);
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'capability_score_adjustments') THEN
            CREATE INDEX IF NOT EXISTS ix_capability_score_adj_target_type ON capability_score_adjustments(target_urn, target_type);
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'outbox_events') THEN
            CREATE INDEX IF NOT EXISTS ix_outbox_events_status_created ON outbox_events(status, created_at);
        END IF;
    END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_outbox_events_status_created;")
    op.execute("DROP INDEX IF EXISTS ix_capability_score_adj_target_type;")
    op.execute("DROP INDEX IF EXISTS ix_attribution_entries_review_dimension;")
