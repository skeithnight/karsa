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
    # Attribution entries — write-once, variable cardinality
    op.execute("""
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
    """)

    op.execute("COMMENT ON TABLE attribution_entries IS 'Write-once ledger entry for attribution tracking. Variable cardinality per review per dimension.';")
    op.execute("COMMENT ON COLUMN attribution_entries.dimension IS 'WORKER, ALLOCATION, CIO, or PORTFOLIO.';")
    op.execute("COMMENT ON COLUMN attribution_entries.attribution_type IS 'POSITIVE, NEGATIVE, or NEUTRAL. Derived from contribution_bps sign.';")

    # Indexes
    op.execute("CREATE INDEX ix_attribution_entries_review_id ON attribution_entries(review_id);")
    op.execute("CREATE INDEX ix_attribution_entries_dimension ON attribution_entries(dimension);")
    op.execute("CREATE INDEX ix_attribution_entries_target_urn ON attribution_entries(target_urn);")

    # Immutability trigger
    op.execute("""
    CREATE OR REPLACE FUNCTION block_attribution_entries_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'attribution_entries is immutable';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_block_attribution_entries_update
        BEFORE UPDATE ON attribution_entries
        FOR EACH ROW EXECUTE FUNCTION block_attribution_entries_mutation();
    """)

    op.execute("""
    CREATE TRIGGER trg_block_attribution_entries_delete
        BEFORE DELETE ON attribution_entries
        FOR EACH ROW EXECUTE FUNCTION block_attribution_entries_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_attribution_entries_delete ON attribution_entries;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_attribution_entries_update ON attribution_entries;")
    op.execute("DROP FUNCTION IF EXISTS block_attribution_entries_mutation();")
    op.execute("DROP TABLE IF EXISTS attribution_entries;")
