"""sprint10 review_version_registry

Revision ID: 102
Revises: 101
Create Date: 2026-06-20

"""
from alembic import op

revision = '102'
down_revision = '101'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review version registry — mutable governance table (ADR-107)
    # Canonical governance handled exclusively here
    op.execute("""
    CREATE TABLE review_version_registry (
        version_id          VARCHAR(64)   NOT NULL DEFAULT gen_random_uuid()::VARCHAR,
        evaluation_id       VARCHAR(64)   NOT NULL,
        review_type         VARCHAR(32)   NOT NULL,
        review_version      VARCHAR(32)   NOT NULL,
        review_id           VARCHAR(64)   NOT NULL,
        review_status       VARCHAR(16)   NOT NULL DEFAULT 'CANONICAL',
        superseded_by       VARCHAR(64),
        created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        CONSTRAINT pk_review_version_registry PRIMARY KEY (version_id),
        CONSTRAINT uq_review_evaluation_type_version UNIQUE (evaluation_id, review_type, review_version),
        CONSTRAINT fk_review_version_review FOREIGN KEY (review_id) REFERENCES review_assessments(review_id),
        CONSTRAINT chk_review_status CHECK (review_status IN ('CANONICAL', 'SUPERSEDED', 'EXPERIMENTAL'))
    );
    """)

    op.execute("COMMENT ON TABLE review_version_registry IS 'Canonical review governance. ADR-107. Exactly one CANONICAL per (evaluation_id, review_type).';")

    # Partial unique index enforcing single canonical per evaluation+type (ADR-107)
    op.execute("""
    CREATE UNIQUE INDEX uq_single_canonical_per_evaluation_type
    ON review_version_registry(evaluation_id, review_type)
    WHERE review_status = 'CANONICAL';
    """)

    # Indexes
    op.execute("CREATE INDEX idx_review_version_status ON review_version_registry(review_status);")
    op.execute("CREATE INDEX idx_review_version_evaluation ON review_version_registry(evaluation_id);")
    op.execute("CREATE INDEX idx_review_version_type ON review_version_registry(review_type);")
    op.execute("CREATE INDEX idx_review_version_review ON review_version_registry(review_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_version_registry;")
