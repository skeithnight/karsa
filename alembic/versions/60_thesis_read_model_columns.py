"""Add missing columns to thesis_snapshots for read models

Revision ID: 60
Revises: 55
Create Date: 2026-06-19 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '60'
down_revision = '55_post_mortem_records_init'
branch_labels = None
depends_on = None

def upgrade():
    # Add missing columns to thesis_snapshots (will automatically apply to partitions)
    op.execute("""
        ALTER TABLE thesis_snapshots
        ADD COLUMN title TEXT,
        ADD COLUMN lifecycle_state TEXT,
        ADD COLUMN confidence NUMERIC DEFAULT 0.0,
        ADD COLUMN author_urn TEXT,
        ADD COLUMN regime_urn TEXT,
        ADD COLUMN summary TEXT,
        ADD COLUMN rationale TEXT,
        ADD COLUMN assumptions_jsonb JSONB;
    """)

def downgrade():
    op.execute("""
        ALTER TABLE thesis_snapshots
        DROP COLUMN title,
        DROP COLUMN lifecycle_state,
        DROP COLUMN confidence,
        DROP COLUMN author_urn,
        DROP COLUMN regime_urn,
        DROP COLUMN summary,
        DROP COLUMN rationale,
        DROP COLUMN assumptions_jsonb;
    """)
