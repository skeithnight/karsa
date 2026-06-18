"""evidence registry

Revision ID: 52_evidence_registry
Revises: 51_foundation_remediation
Create Date: 2026-06-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '52_evidence_registry'
down_revision = '51_foundation_remediation'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('promoted_evidence',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('evidence_id', sa.String(length=255), nullable=False),
        sa.Column('source_blob_id', sa.String(length=255), nullable=False),
        sa.Column('provider_id', sa.String(length=255), nullable=False),
        sa.Column('asset_id', sa.String(length=255), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_promoted_evidence_evidence_id'), 'promoted_evidence', ['evidence_id'], unique=True)
    op.create_index(op.f('ix_promoted_evidence_source_blob_id'), 'promoted_evidence', ['source_blob_id'], unique=False)
    op.create_index(op.f('ix_promoted_evidence_asset_id'), 'promoted_evidence', ['asset_id'], unique=False)
    op.create_index(op.f('ix_promoted_evidence_payload_hash'), 'promoted_evidence', ['payload_hash'], unique=False)

def downgrade() -> None:
    op.drop_table('promoted_evidence')
