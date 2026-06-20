"""sprint07 review_cycles decision_id unique constraint

Revision ID: 80
Revises: 79
Create Date: 2026-06-20

"""
from alembic import op

revision = '80'
down_revision = '79'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enforce idempotency: each decision_id can have at most one review cycle.
    # This eliminates the application-level check-then-insert race condition.
    op.execute("""
    CREATE UNIQUE INDEX ux_review_cycles_decision_id
    ON review_cycles(decision_id);
    """)

    op.execute("COMMENT ON INDEX ux_review_cycles_decision_id IS 'Enforces one review cycle per CIO decision. Eliminates idempotency race condition.';")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_review_cycles_decision_id;")
