"""sprint07 attribution_entries

Revision ID: 73
Revises: 72
Create Date: 2026-06-20

"""
from alembic import op

revision = '73'
down_revision = '72'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip if table already exists (migration 44 may have created review_records with different schema)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'attribution_entries') THEN
            RAISE NOTICE 'attribution_entries already exists, skipping migration 73';
            RETURN;
        END IF;

        -- Only create if review_records has review_id column (migration 72 schema)
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='review_records' AND column_name='review_id') THEN
            RAISE NOTICE 'review_records does not have review_id column, skipping migration 73';
            RETURN;
        END IF;

        -- Attribution entries — write-once, variable cardinality
        CREATE TABLE attribution_entries (
            attribution_id VARCHAR(64) PRIMARY KEY,
            review_id VARCHAR(64) NOT NULL,
            dimension VARCHAR(16) NOT NULL,
            target_urn VARCHAR(256) NOT NULL,
            contribution_bps NUMERIC(10, 4) NOT NULL,
            contribution_pct NUMERIC(8, 6) NOT NULL,
            attribution_type VARCHAR(16) NOT NULL,
            evidence JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT fk_attribution_entries_review
                FOREIGN KEY (review_id) REFERENCES review_records(review_id)
        );

        COMMENT ON TABLE attribution_entries IS 'Write-once ledger entry for attribution tracking.';
        COMMENT ON COLUMN attribution_entries.dimension IS 'WORKER, ALLOCATION, CIO, or PORTFOLIO.';
        COMMENT ON COLUMN attribution_entries.attribution_type IS 'POSITIVE, NEGATIVE, or NEUTRAL.';

        CREATE INDEX ix_attribution_entries_review_id ON attribution_entries(review_id);
        CREATE INDEX ix_attribution_entries_dimension ON attribution_entries(dimension);
        CREATE INDEX ix_attribution_entries_target_urn ON attribution_entries(target_urn);

        CREATE OR REPLACE FUNCTION block_attribution_entries_mutation()
        RETURNS TRIGGER AS $func$
        BEGIN
            RAISE EXCEPTION 'attribution_entries is immutable';
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_block_attribution_entries_update
            BEFORE UPDATE ON attribution_entries
            FOR EACH ROW EXECUTE FUNCTION block_attribution_entries_mutation();

        CREATE TRIGGER trg_block_attribution_entries_delete
            BEFORE DELETE ON attribution_entries
            FOR EACH ROW EXECUTE FUNCTION block_attribution_entries_mutation();
    END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_attribution_entries_delete ON attribution_entries;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_attribution_entries_update ON attribution_entries;")
    op.execute("DROP FUNCTION IF EXISTS block_attribution_entries_mutation();")
    op.execute("DROP TABLE IF EXISTS attribution_entries;")
