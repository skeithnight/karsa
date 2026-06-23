"""sprint07 capability_score_adjustments

Revision ID: 74
Revises: 73
Create Date: 2026-06-20

"""
from alembic import op

revision = '74'
down_revision = '73'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip if table already exists or review_records doesn't have review_id
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'capability_score_adjustments') THEN
            RAISE NOTICE 'capability_score_adjustments already exists, skipping migration 74';
            RETURN;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='review_records' AND column_name='review_id') THEN
            RAISE NOTICE 'review_records does not have review_id column, skipping migration 74';
            RETURN;
        END IF;

        -- Capability score adjustments — write-once, delta only
        CREATE TABLE capability_score_adjustments (
            adjustment_id VARCHAR(64) PRIMARY KEY,
            target_urn VARCHAR(256) NOT NULL,
            target_type VARCHAR(32) NOT NULL,
            score_delta NUMERIC(10, 6) NOT NULL,
            confidence_delta NUMERIC(6, 4) NOT NULL,
            review_id VARCHAR(64) NOT NULL,
            rationale TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT fk_capability_score_adj_review
                FOREIGN KEY (review_id) REFERENCES review_records(review_id)
        );

        COMMENT ON TABLE capability_score_adjustments IS 'Write-once ledger entry for capability score adjustments.';
        COMMENT ON COLUMN capability_score_adjustments.target_type IS 'WORKER, THESIS, or STRATEGY.';
        COMMENT ON COLUMN capability_score_adjustments.score_delta IS 'Score change in decimal. Positive = improvement, negative = degradation.';

        CREATE INDEX ix_capability_score_adj_target_urn ON capability_score_adjustments(target_urn);
        CREATE INDEX ix_capability_score_adj_review_id ON capability_score_adjustments(review_id);
        CREATE INDEX ix_capability_score_adj_created_at ON capability_score_adjustments(created_at);

        CREATE OR REPLACE FUNCTION block_capability_score_adj_mutation()
        RETURNS TRIGGER AS $func$
        BEGIN
            RAISE EXCEPTION 'capability_score_adjustments is immutable';
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_block_capability_score_adj_update
            BEFORE UPDATE ON capability_score_adjustments
            FOR EACH ROW EXECUTE FUNCTION block_capability_score_adj_mutation();

        CREATE TRIGGER trg_block_capability_score_adj_delete
            BEFORE DELETE ON capability_score_adjustments
            FOR EACH ROW EXECUTE FUNCTION block_capability_score_adj_mutation();
    END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_capability_score_adj_delete ON capability_score_adjustments;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_capability_score_adj_update ON capability_score_adjustments;")
    op.execute("DROP FUNCTION IF EXISTS block_capability_score_adj_mutation();")
    op.execute("DROP TABLE IF EXISTS capability_score_adjustments;")
