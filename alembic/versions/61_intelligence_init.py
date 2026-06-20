"""intelligence init

Revision ID: 61_intelligence_init
Revises: 60
Create Date: 2026-06-19 14:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '61'
down_revision = '60'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # dim_worker
    op.create_table(
        'dim_worker',
        sa.Column('dim_worker_id', sa.Integer(), nullable=False),
        sa.Column('worker_urn', sa.String(), nullable=False),
        sa.Column('subject_type', sa.String(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('dim_worker_id')
    )
    op.create_index('ix_dim_worker_urn_current', 'dim_worker', ['worker_urn', 'is_current'], unique=False)

    # dim_regime
    op.create_table(
        'dim_regime',
        sa.Column('dim_regime_id', sa.Integer(), nullable=False),
        sa.Column('regime_urn', sa.String(), nullable=False),
        sa.Column('regime_type', sa.String(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('dim_regime_id')
    )

    # fact_capability_transition
    op.create_table(
        'fact_capability_transition',
        sa.Column('fact_id', sa.Integer(), nullable=False),
        sa.Column('dim_worker_id', sa.Integer(), nullable=False),
        sa.Column('old_state', sa.String(), nullable=False),
        sa.Column('new_state', sa.String(), nullable=False),
        sa.Column('authority', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['dim_worker_id'], ['dim_worker.dim_worker_id'], ),
        sa.PrimaryKeyConstraint('fact_id'),
        sa.UniqueConstraint('event_sequence', name='uq_fact_capability_event_sequence')
    )

    # fact_alpha_generation
    op.create_table(
        'fact_alpha_generation',
        sa.Column('fact_id', sa.Integer(), nullable=False),
        sa.Column('dim_worker_id', sa.Integer(), nullable=False),
        sa.Column('dim_regime_id', sa.Integer(), nullable=True),
        sa.Column('alpha_delta', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('cumulative_alpha', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['dim_regime_id'], ['dim_regime.dim_regime_id'], ),
        sa.ForeignKeyConstraint(['dim_worker_id'], ['dim_worker.dim_worker_id'], ),
        sa.PrimaryKeyConstraint('fact_id'),
        sa.UniqueConstraint('event_sequence', name='uq_fact_alpha_event_sequence')
    )

    # edge_swarm_attribution
    op.create_table(
        'edge_swarm_attribution',
        sa.Column('edge_id', sa.Integer(), nullable=False),
        sa.Column('parent_worker_urn', sa.String(), nullable=True),
        sa.Column('child_worker_urn', sa.String(), nullable=False),
        sa.Column('attribution_urn', sa.String(), nullable=False),
        sa.Column('skill_ratio', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('edge_id'),
        sa.UniqueConstraint('event_sequence', name='uq_edge_swarm_event_sequence')
    )

def downgrade() -> None:
    op.drop_table('edge_swarm_attribution')
    op.drop_table('fact_alpha_generation')
    op.drop_table('fact_capability_transition')
    op.drop_table('dim_regime')
    op.drop_table('dim_worker')
