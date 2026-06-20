"""sprint07 review_coverage_projection

Revision ID: 77
Revises: 76
Create Date: 2026-06-20

"""
from alembic import op

revision = '77'
down_revision = '76'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review coverage projection — derived from eligibility events
    # Mutable: status updated as lifecycle progresses
    op.execute("""
    CREATE TABLE review_coverage_projection (
        decision_id VARCHAR(64) PRIMARY KEY,
        proposal_id VARCHAR(64),
        cycle_id VARCHAR(64),
        eligible BOOLEAN NOT NULL DEFAULT false,
        review_type VARCHAR(32),
        strategy_name VARCHAR(128),
        strategy_version VARCHAR(32),
        evaluation_reason TEXT,
        review_status VARCHAR(16) NOT NULL DEFAULT 'NO_REVIEW',
        review_due_date TIMESTAMPTZ,
        executed_at TIMESTAMPTZ,
        days_overdue INTEGER,
        evaluated_at TIMESTAMPTZ NOT NULL
    );
    """)

    op.execute("COMMENT ON TABLE review_coverage_projection IS 'Derived projection: tracks review coverage for all evaluated decisions. NO_REVIEW derived from eligible=false event.';")
    op.execute("COMMENT ON COLUMN review_coverage_projection.review_status IS 'NO_REVIEW, PENDING, DUE, OVERDUE, EXECUTED. Derived from lifecycle events.';")

    # Indexes
    op.execute("CREATE INDEX ix_review_coverage_status ON review_coverage_projection(review_status);")
    op.execute("CREATE INDEX ix_review_coverage_eligible ON review_coverage_projection(eligible);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_coverage_projection;")
