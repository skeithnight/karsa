"""sprint09 attribution_records

Revision ID: 95
Revises: 80
Create Date: 2026-06-20

"""
from alembic import op

revision = '95'
down_revision = '80'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attribution records — write-once ledger entry (ADR-093)
    # Business identity: UNIQUE(evaluation_id, algorithm_version) (ADR-094)
    op.execute("""
    CREATE TABLE attribution_records (
        attribution_id      VARCHAR(64)   NOT NULL,
        evaluation_id       VARCHAR(64)   NOT NULL,
        algorithm_version   VARCHAR(32)   NOT NULL,
        decision_id         VARCHAR(64)   NOT NULL,
        evaluation_horizon_days INTEGER    NOT NULL,
        target_urn          VARCHAR(256)  NOT NULL,
        target_type         VARCHAR(32)   NOT NULL,
        total_realized_return_bps  NUMERIC(12,4) NOT NULL,
        total_expected_return_bps  NUMERIC(12,4) NOT NULL,
        total_variance_bps         NUMERIC(12,4) NOT NULL,
        contributions       JSONB         NOT NULL,
        attribution_summary JSONB         NOT NULL,
        attribution_quality JSONB         NOT NULL,
        quality_provenance  JSONB         NOT NULL DEFAULT '{}'::jsonb,
        context_snapshot    JSONB         NOT NULL,
        source_request_id   VARCHAR(64)   NOT NULL,
        attributed_at       TIMESTAMPTZ   NOT NULL,
        attributed_by       VARCHAR(64)   NOT NULL,
        created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        CONSTRAINT pk_attribution_records PRIMARY KEY (attribution_id),
        CONSTRAINT uq_evaluation_algorithm UNIQUE (evaluation_id, algorithm_version)
    );
    """)

    op.execute("COMMENT ON TABLE attribution_records IS 'Write-once attribution ledger. ADR-093. Canonical governance via attribution_version_registry.';")

    # Immutability trigger (ADR-093)
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_attribution_record_update()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'attribution_records is immutable (ADR-093)';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_attribution_record_immutable
        BEFORE UPDATE ON attribution_records
        FOR EACH ROW EXECUTE FUNCTION prevent_attribution_record_update();
    """)

    op.execute("""
    CREATE TRIGGER trg_attribution_record_no_delete
        BEFORE DELETE ON attribution_records
        FOR EACH ROW EXECUTE FUNCTION prevent_attribution_record_update();
    """)

    # Indexes
    op.execute("CREATE INDEX idx_attribution_evaluation ON attribution_records(evaluation_id);")
    op.execute("CREATE INDEX idx_attribution_algorithm ON attribution_records(algorithm_version);")
    op.execute("CREATE INDEX idx_attribution_target ON attribution_records(target_urn);")
    op.execute("CREATE INDEX idx_attribution_decision ON attribution_records(decision_id);")
    op.execute("CREATE INDEX idx_attribution_created ON attribution_records(created_at);")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_attribution_record_no_delete ON attribution_records;")
    op.execute("DROP TRIGGER IF EXISTS trg_attribution_record_immutable ON attribution_records;")
    op.execute("DROP FUNCTION IF EXISTS prevent_attribution_record_update();")
    op.execute("DROP TABLE IF EXISTS attribution_records;")
