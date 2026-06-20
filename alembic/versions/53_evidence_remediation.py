"""evidence remediation

Revision ID: 53_evidence_remediation
Revises: 52_evidence_registry
Create Date: 2026-06-17 18:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '53_evidence_remediation'
down_revision = '52_evidence_registry'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add extracted_at
    op.add_column('promoted_evidence', sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE promoted_evidence SET extracted_at = promoted_at WHERE extracted_at IS NULL")
    op.alter_column('promoted_evidence', 'extracted_at', nullable=False)
    
    # payload_hash was an index, we need to make it unique
    op.drop_index('ix_promoted_evidence_payload_hash', table_name='promoted_evidence')
    op.create_index(op.f('ix_promoted_evidence_payload_hash'), 'promoted_evidence', ['payload_hash'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_promoted_evidence_payload_hash'), table_name='promoted_evidence')
    op.create_index('ix_promoted_evidence_payload_hash', 'promoted_evidence', ['payload_hash'], unique=False)
    op.drop_column('promoted_evidence', 'extracted_at')
