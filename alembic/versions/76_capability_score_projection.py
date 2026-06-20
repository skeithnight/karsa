"""sprint07 capability_score_projection

Revision ID: 76
Revises: 75
Create Date: 2026-06-20

"""
from alembic import op

revision = '76'
down_revision = '75'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Capability score projection — derived from SUM(score_delta)
    # Mutable: current_score updated via UPSERT
    op.execute("""
    CREATE TABLE capability_score_projection (
        target_urn VARCHAR(256) PRIMARY KEY,
        target_type VARCHAR(32) NOT NULL,
        current_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
        current_confidence NUMERIC(6, 4) NOT NULL DEFAULT 0,
        adjustment_count INTEGER NOT NULL DEFAULT 0,
        last_updated TIMESTAMPTZ NOT NULL
    );
    """)

    op.execute("COMMENT ON TABLE capability_score_projection IS 'Derived projection: current score = SUM(score_delta) from capability_score_adjustments. Mutable via UPSERT.';")
    op.execute("COMMENT ON COLUMN capability_score_projection.current_score IS 'SUM of all score_delta for this target_urn.';")
    op.execute("COMMENT ON COLUMN capability_score_projection.adjustment_count IS 'COUNT of adjustments for this target_urn.';")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS capability_score_projection;")
