"""sprint06 proposal_status_projection

Revision ID: 68
Revises: 67
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = '68'
down_revision = '67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE proposal_status_projection (
        proposal_id VARCHAR(64) PRIMARY KEY,
        status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
        decision_id VARCHAR(64),
        decided_at TIMESTAMPTZ,
        decided_by VARCHAR(64),
        event_sequence BIGINT NOT NULL DEFAULT 0
    );
    """)

    op.execute("CREATE INDEX ix_proposal_status ON proposal_status_projection(status);")
    op.execute("CREATE INDEX ix_proposal_status_sequence ON proposal_status_projection(event_sequence);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS proposal_status_projection;")
