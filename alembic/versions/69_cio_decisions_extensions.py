"""sprint06 cio_decisions extensions

Revision ID: 69
Revises: 68
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = '69'
down_revision = '68'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE cio_decisions ADD COLUMN IF NOT EXISTS proposal_id VARCHAR(64);")
    op.execute("ALTER TABLE cio_decisions ADD COLUMN IF NOT EXISTS expected_outcome JSONB;")
    op.execute("ALTER TABLE cio_decisions ADD COLUMN IF NOT EXISTS risk_assessment JSONB;")
    op.execute("ALTER TABLE cio_decisions ADD COLUMN IF NOT EXISTS review_horizon JSONB;")


def downgrade() -> None:
    op.execute("ALTER TABLE cio_decisions DROP COLUMN IF EXISTS review_horizon;")
    op.execute("ALTER TABLE cio_decisions DROP COLUMN IF EXISTS risk_assessment;")
    op.execute("ALTER TABLE cio_decisions DROP COLUMN IF EXISTS expected_outcome;")
    op.execute("ALTER TABLE cio_decisions DROP COLUMN IF EXISTS proposal_id;")
