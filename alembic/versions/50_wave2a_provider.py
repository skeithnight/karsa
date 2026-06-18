"""wave2a provider platform

Revision ID: 50_wave2a_provider
Revises: 49_wave1_remediation
Create Date: 2026-06-17 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '50_wave2a_provider'
down_revision = '49_wave1_remediation'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # provider_definitions
    op.create_table('provider_definitions',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('provider_id', sa.String(length=255), nullable=False),
        sa.Column('provider_name', sa.String(length=255), nullable=False),
        sa.Column('provider_type', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_definitions_provider_id'), 'provider_definitions', ['provider_id'], unique=True)

    # provider_health
    op.create_table('provider_health',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('provider_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_health_provider_id'), 'provider_health', ['provider_id'], unique=True)

    # provider_datalake_blobs
    op.create_table('provider_datalake_blobs',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('blob_id', sa.String(length=255), nullable=False),
        sa.Column('provider_id', sa.String(length=255), nullable=False),
        sa.Column('asset_id', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_datalake_blobs_blob_id'), 'provider_datalake_blobs', ['blob_id'], unique=True)
    op.create_index(op.f('ix_provider_datalake_blobs_provider_id'), 'provider_datalake_blobs', ['provider_id'], unique=False)
    op.create_index(op.f('ix_provider_datalake_blobs_asset_id'), 'provider_datalake_blobs', ['asset_id'], unique=False)

def downgrade() -> None:
    op.drop_table('provider_datalake_blobs')
    op.drop_table('provider_health')
    op.drop_table('provider_definitions')
