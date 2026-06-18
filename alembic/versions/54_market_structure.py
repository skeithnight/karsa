"""market structure

Revision ID: 54_market_structure
Revises: 53_evidence_remediation
Create Date: 2026-06-17 18:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '54_market_structure'
down_revision = '53_evidence_remediation'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Market Universes
    op.create_table('market_universes',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('universe_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_universes_universe_id'), 'market_universes', ['universe_id'], unique=True)
    
    # Universe Members
    op.create_table('universe_members_table',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('universe_id', sa.String(length=255), nullable=False),
        sa.Column('asset_id', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['universe_id'], ['market_universes.universe_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_universe_members_table_asset_id'), 'universe_members_table', ['asset_id'], unique=False)
    op.create_index(op.f('ix_universe_members_table_universe_id'), 'universe_members_table', ['universe_id'], unique=False)
    
    # Market Structure Snapshots
    op.create_table('market_structure_snapshots',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('snapshot_id', sa.String(length=255), nullable=False),
        sa.Column('advancers', sa.Integer(), nullable=False),
        sa.Column('decliners', sa.Integer(), nullable=False),
        sa.Column('new_highs', sa.Integer(), nullable=False),
        sa.Column('new_lows', sa.Integer(), nullable=False),
        sa.Column('sector_strength', sa.JSON(), nullable=False),
        sa.Column('foreign_flow_anomalies', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_structure_snapshots_snapshot_id'), 'market_structure_snapshots', ['snapshot_id'], unique=True)

def downgrade() -> None:
    op.drop_table('market_structure_snapshots')
    op.drop_table('universe_members_table')
    op.drop_table('market_universes')
