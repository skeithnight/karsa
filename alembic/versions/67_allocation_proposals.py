"""sprint06 allocation_proposals

Revision ID: 67
Revises: da0ed664092f
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = '67'
down_revision = 'da0ed664092f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE allocation_proposals (
        proposal_id VARCHAR(64) PRIMARY KEY,
        policy_id VARCHAR(64) NOT NULL,
        policy_snapshot JSONB NOT NULL,
        journal_ref VARCHAR(64) NOT NULL,
        proposed_weights JSONB NOT NULL,
        total_capital NUMERIC(15, 4) NOT NULL,
        proposal_rationale TEXT NOT NULL,
        portfolio_context JSONB NOT NULL,
        context_hash VARCHAR(64) NOT NULL,
        generated_at TIMESTAMPTZ NOT NULL
    );
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION block_proposal_mutation()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'allocation_proposals is immutable';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_block_proposal_update
        BEFORE UPDATE ON allocation_proposals
        FOR EACH ROW EXECUTE FUNCTION block_proposal_mutation();
    """)

    op.execute("""
    CREATE TRIGGER trg_block_proposal_delete
        BEFORE DELETE ON allocation_proposals
        FOR EACH ROW EXECUTE FUNCTION block_proposal_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_proposal_delete ON allocation_proposals;")
    op.execute("DROP TRIGGER IF EXISTS trg_block_proposal_update ON allocation_proposals;")
    op.execute("DROP FUNCTION IF EXISTS block_proposal_mutation();")
    op.execute("DROP TABLE IF EXISTS allocation_proposals;")
