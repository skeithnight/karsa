"""Sprint-49 Observability

Revision ID: sprint49_obs
Revises: 001_sprint48_remediation
Create Date: 2026-06-15 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'sprint49_obs'
down_revision = '001_sprint48_remediation'

def upgrade():
    op.create_table(
        'observability_traces',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('trace_id', sa.String(255), nullable=False, index=True),
        sa.Column('correlation_id', sa.String(255), nullable=False),
        sa.Column('causation_id', sa.String(255), nullable=False),
        sa.Column('operation_name', sa.String(255), nullable=False),
        sa.Column('properties', JSONB, nullable=False),
        sa.Column('start_time', sa.DateTime, nullable=False),
        sa.Column('end_time', sa.DateTime, nullable=True)
    )
    
    op.create_table(
        'observability_metrics',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('value', sa.Numeric, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

    op.create_table(
        'observability_worker_states',
        sa.Column('worker_id', sa.String(255), primary_key=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

    op.create_table(
        'observability_queue_states',
        sa.Column('queue_name', sa.String(255), primary_key=True),
        sa.Column('pending_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

def downgrade():
    op.drop_table('observability_queue_states')
    op.drop_table('observability_worker_states')
    op.drop_table('observability_metrics')
    op.drop_table('observability_traces')
