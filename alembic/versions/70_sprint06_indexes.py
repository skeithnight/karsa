"""sprint06 indexes

Revision ID: 70
Revises: 69
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = '70'
down_revision = '69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_cio_decisions_proposal_id ON cio_decisions(proposal_id);")
    op.execute("CREATE INDEX ix_allocation_proposals_generated_at ON allocation_proposals(generated_at);")
    op.execute("CREATE INDEX ix_allocation_proposals_policy_id ON allocation_proposals(policy_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_allocation_proposals_policy_id;")
    op.execute("DROP INDEX IF EXISTS ix_allocation_proposals_generated_at;")
    op.execute("DROP INDEX IF EXISTS ix_cio_decisions_proposal_id;")
