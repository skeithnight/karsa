"""sprint10 review_assessments

Revision ID: 101
Revises: 98
Create Date: 2026-06-20

"""
from alembic import op

revision = '101'
down_revision = '98'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Review assessments — write-once ledger entry (ADR-106)
    # Business identity: UNIQUE(evaluation_id, review_type, review_version)
    op.execute("""
    CREATE TABLE review_assessments (
        review_id           VARCHAR(64)   NOT NULL,
        evaluation_id       VARCHAR(64)   NOT NULL,
        review_type         VARCHAR(32)   NOT NULL,
        review_version      VARCHAR(32)   NOT NULL,
        target_urn          VARCHAR(256)  NOT NULL,
        target_type         VARCHAR(32)   NOT NULL,
        decision_id         VARCHAR(64)   NOT NULL,
        attribution_id      VARCHAR(64)   NOT NULL,
        findings            JSONB         NOT NULL,
        recommendations     JSONB         NOT NULL,
        review_summary      JSONB         NOT NULL,
        review_quality      JSONB         NOT NULL,
        context_snapshot    JSONB         NOT NULL,
        reviewed_at         TIMESTAMPTZ   NOT NULL,
        reviewed_by         VARCHAR(64)   NOT NULL,
        created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
        CONSTRAINT pk_review_assessments PRIMARY KEY (review_id),
        CONSTRAINT uq_review_assessment_identity UNIQUE (evaluation_id, review_type, review_version)
    );
    """)

    op.execute("COMMENT ON TABLE review_assessments IS 'Write-once review ledger. ADR-106. Canonical governance via review_version_registry.';")

    # Immutability trigger (ADR-106)
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_review_assessment_update()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'review_assessments is immutable (ADR-106)';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_review_assessment_immutable
        BEFORE UPDATE ON review_assessments
        FOR EACH ROW EXECUTE FUNCTION prevent_review_assessment_update();
    """)

    op.execute("""
    CREATE TRIGGER trg_review_assessment_no_delete
        BEFORE DELETE ON review_assessments
        FOR EACH ROW EXECUTE FUNCTION prevent_review_assessment_update();
    """)

    # Indexes
    op.execute("CREATE INDEX ix_review_assessment_evaluation ON review_assessments(evaluation_id);")
    op.execute("CREATE INDEX ix_review_assessment_type ON review_assessments(review_type);")
    op.execute("CREATE INDEX ix_review_assessment_target ON review_assessments(target_urn);")
    op.execute("CREATE INDEX ix_review_assessment_decision ON review_assessments(decision_id);")
    op.execute("CREATE INDEX ix_review_assessment_created ON review_assessments(created_at);")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_review_assessment_no_delete ON review_assessments;")
    op.execute("DROP TRIGGER IF EXISTS trg_review_assessment_immutable ON review_assessments;")
    op.execute("DROP FUNCTION IF EXISTS prevent_review_assessment_update();")
    op.execute("DROP TABLE IF EXISTS review_assessments;")
