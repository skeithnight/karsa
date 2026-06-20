"""firm intelligence datamart

Revision ID: 006_firm_intel
Revises: 005_review_attr
Create Date: 2026-06-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_firm_intel'
down_revision = '005_review_attr'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # SCD2 Dimensions
    op.create_table(
        'dim_worker',
        sa.Column('dim_worker_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('worker_urn', sa.String(255), nullable=False),
        sa.Column('subject_type', sa.String(50), nullable=False),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_to', sa.DateTime(), server_default='9999-12-31 23:59:59', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False)
    )
    op.create_index('ix_dim_worker_urn', 'dim_worker', ['worker_urn'])
    op.create_index('ix_dim_worker_current', 'dim_worker', ['worker_urn', 'is_current'])

    op.create_table(
        'dim_regime',
        sa.Column('dim_regime_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('regime_urn', sa.String(255), nullable=False),
        sa.Column('regime_type', sa.String(50), nullable=False),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_to', sa.DateTime(), server_default='9999-12-31 23:59:59', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False)
    )
    op.create_index('ix_dim_regime_urn', 'dim_regime', ['regime_urn'])
    op.create_index('ix_dim_regime_current', 'dim_regime', ['regime_urn', 'is_current'])

    op.create_table(
        'dim_policy',
        sa.Column('dim_policy_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('policy_urn', sa.String(255), nullable=False),
        sa.Column('policy_version', sa.Integer(), nullable=False),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('effective_to', sa.DateTime(), server_default='9999-12-31 23:59:59', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False)
    )

    # Facts
    op.create_table(
        'fact_alpha_generation',
        sa.Column('fact_id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('dim_worker_id', sa.Integer(), sa.ForeignKey('dim_worker.dim_worker_id')),
        sa.Column('dim_regime_id', sa.Integer(), sa.ForeignKey('dim_regime.dim_regime_id')),
        sa.Column('alpha_delta', sa.Float(), nullable=False),
        sa.Column('cumulative_alpha', sa.Float(), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('event_sequence', name='uq_fact_alpha_event_sequence')
    )

    op.create_table(
        'fact_capability_transition',
        sa.Column('fact_id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('dim_worker_id', sa.Integer(), sa.ForeignKey('dim_worker.dim_worker_id')),
        sa.Column('dim_policy_id', sa.Integer(), sa.ForeignKey('dim_policy.dim_policy_id')),
        sa.Column('old_state', sa.String(50), nullable=False),
        sa.Column('new_state', sa.String(50), nullable=False),
        sa.Column('authority', sa.String(50), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('event_sequence', name='uq_fact_capability_event_sequence')
    )

    op.create_table(
        'fact_calibration_grade',
        sa.Column('fact_id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('dim_worker_id', sa.Integer(), sa.ForeignKey('dim_worker.dim_worker_id')),
        sa.Column('calibration_delta', sa.Float(), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('event_sequence', name='uq_fact_calibration_event_sequence')
    )

    # Graph
    op.create_table(
        'edge_swarm_attribution',
        sa.Column('edge_id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('parent_worker_urn', sa.String(255), nullable=True),
        sa.Column('child_worker_urn', sa.String(255), nullable=False),
        sa.Column('attribution_urn', sa.String(255), nullable=False),
        sa.Column('skill_ratio', sa.Float(), nullable=False),
        sa.Column('event_sequence', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('event_sequence', name='uq_edge_swarm_event_sequence')
    )
    
    # Example View (vw_governance_suspension_audit)
    op.execute("""
    CREATE MATERIALIZED VIEW vw_governance_suspension_audit AS
    SELECT f.fact_id, w.worker_urn, f.old_state, f.new_state, f.authority, f.reason, f.event_timestamp
    FROM fact_capability_transition f
    JOIN dim_worker w ON f.dim_worker_id = w.dim_worker_id
    WHERE f.authority = 'RISK_OFFICER';
    """)

def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW vw_governance_suspension_audit")
    op.drop_table('edge_swarm_attribution')
    op.drop_table('fact_calibration_grade')
    op.drop_table('fact_capability_transition')
    op.drop_table('fact_alpha_generation')
    op.drop_table('dim_policy')
    op.drop_table('dim_regime')
    op.drop_table('dim_worker')
