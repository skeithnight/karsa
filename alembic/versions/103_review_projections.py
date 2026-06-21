"""sprint10 review projections

Revision ID: 103
Revises: 102
Create Date: 2026-06-20

"""
from alembic import op

revision = '103'
down_revision = '102'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Worker review projection (derived, mutable)
    op.execute("""
    CREATE TABLE worker_review_projection (
        target_urn VARCHAR(256) PRIMARY KEY,
        total_reviews INTEGER NOT NULL DEFAULT 0,
        avg_quality_score NUMERIC(5,4) NOT NULL DEFAULT 0,
        total_findings INTEGER NOT NULL DEFAULT 0,
        total_recommendations INTEGER NOT NULL DEFAULT 0,
        last_reviewed TIMESTAMPTZ
    );
    """)

    # Thesis review projection (derived, mutable)
    op.execute("""
    CREATE TABLE thesis_review_projection (
        thesis_urn VARCHAR(256) PRIMARY KEY,
        total_reviews INTEGER NOT NULL DEFAULT 0,
        avg_quality_score NUMERIC(5,4) NOT NULL DEFAULT 0,
        last_reviewed TIMESTAMPTZ
    );
    """)

    # Capability gap projection (derived, mutable)
    op.execute("""
    CREATE TABLE capability_gap_projection (
        target_urn VARCHAR(256) NOT NULL,
        gap_type VARCHAR(32) NOT NULL,
        severity VARCHAR(16) NOT NULL,
        description TEXT NOT NULL,
        identified_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT pk_capability_gap PRIMARY KEY (target_urn, gap_type)
    );
    """)

    # Review coverage projection (derived, mutable)
    # Note: This table may already exist from Sprint-09 Attribution Engine
    op.execute("""
    CREATE TABLE IF NOT EXISTS review_coverage_projection (
        evaluation_id VARCHAR(64) NOT NULL,
        review_type VARCHAR(32) NOT NULL,
        review_status VARCHAR(16) NOT NULL DEFAULT 'NO_REVIEW',
        review_id VARCHAR(64),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT pk_review_coverage PRIMARY KEY (evaluation_id, review_type)
    );
    """)

    op.execute("COMMENT ON TABLE worker_review_projection IS 'Derived projection: worker-level review summary.';")
    op.execute("COMMENT ON TABLE thesis_review_projection IS 'Derived projection: thesis-level review summary.';")
    op.execute("COMMENT ON TABLE capability_gap_projection IS 'Derived projection: identified capability gaps.';")
    op.execute("COMMENT ON TABLE review_coverage_projection IS 'Derived projection: review coverage per evaluation.';")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_coverage_projection;")
    op.execute("DROP TABLE IF EXISTS capability_gap_projection;")
    op.execute("DROP TABLE IF EXISTS thesis_review_projection;")
    op.execute("DROP TABLE IF EXISTS worker_review_projection;")
