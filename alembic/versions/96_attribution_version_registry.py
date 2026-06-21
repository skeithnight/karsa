"""sprint09 attribution_version_registry

Revision ID: 96
Revises: 95
Create Date: 2026-06-20

"""
from alembic import op

revision = '96'
down_revision = '95'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attribution version registry — mutable governance table (ADR-102, ADR-104)
    # Canonical governance is handled exclusively here, NOT in attribution_records
    op.execute("""
    CREATE TABLE attribution_version_registry (
        version_id          VARCHAR(64)   NOT NULL DEFAULT gen_random_uuid()::VARCHAR,
        evaluation_id       VARCHAR(64)   NOT NULL,
        algorithm_version   VARCHAR(32)   NOT NULL,
        attribution_id      VARCHAR(64)   NOT NULL,
        attribution_status  VARCHAR(16)   NOT NULL DEFAULT 'CANONICAL',
        superseded_by       VARCHAR(64),
        created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        CONSTRAINT pk_version_registry PRIMARY KEY (version_id),
        CONSTRAINT uq_version_evaluation_algorithm UNIQUE (evaluation_id, algorithm_version),
        CONSTRAINT fk_version_attribution FOREIGN KEY (attribution_id) REFERENCES attribution_records(attribution_id),
        CONSTRAINT chk_version_status CHECK (attribution_status IN ('CANONICAL', 'SUPERSEDED', 'EXPERIMENTAL'))
    );
    """)

    op.execute("COMMENT ON TABLE attribution_version_registry IS 'Canonical attribution governance. ADR-102, ADR-104. Exactly one CANONICAL per evaluation_id.';")

    # Partial unique index enforcing single canonical per evaluation (ADR-102)
    op.execute("""
    CREATE UNIQUE INDEX uq_single_canonical_per_evaluation
    ON attribution_version_registry(evaluation_id)
    WHERE attribution_status = 'CANONICAL';
    """)

    # Indexes
    op.execute("CREATE INDEX idx_version_status ON attribution_version_registry(attribution_status);")
    op.execute("CREATE INDEX idx_version_evaluation ON attribution_version_registry(evaluation_id);")
    op.execute("CREATE INDEX idx_version_attribution ON attribution_version_registry(attribution_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS attribution_version_registry;")
