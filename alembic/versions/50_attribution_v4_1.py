"""attribution v4.1

Revision ID: 50
Revises: 50_wave2a_provider
Create Date: 2026-06-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '50'
down_revision = '50_wave2a_provider'
branch_labels = None
depends_on = None

def upgrade():
    # 1. attribution_lineages
    op.create_table(
        'attribution_lineages',
        sa.Column('lineage_id', sa.String(64), primary_key=True),
        sa.Column('decision_id', sa.String(255), nullable=False),
        sa.Column('forecast_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_attr_lineage_decision_id', 'attribution_lineages', ['decision_id'])
    op.create_index('ix_attr_forecast_id', 'attribution_lineages', ['forecast_id'])

    # 2. attribution_lineage_nodes
    op.create_table(
        'attribution_lineage_nodes',
        sa.Column('node_id', sa.String(64), primary_key=True),
        sa.Column('lineage_id', sa.String(64), sa.ForeignKey('attribution_lineages.lineage_id', ondelete='CASCADE'), nullable=False),
        sa.Column('capability_id', sa.String(255), nullable=False),
        sa.Column('worker_urn', sa.String(255), nullable=False),
        sa.Column('role', sa.String(255), nullable=False)
    )
    op.create_index('ix_attr_lineage_id_nodes', 'attribution_lineage_nodes', ['lineage_id'])
    op.create_index('ix_attr_capability_id', 'attribution_lineage_nodes', ['capability_id'])

    # 3. attribution_assessments
    op.create_table(
        'attribution_assessments',
        sa.Column('assessment_id', sa.String(64), primary_key=True),
        sa.Column('lineage_id', sa.String(64), sa.ForeignKey('attribution_lineages.lineage_id', ondelete='CASCADE'), nullable=False),
        sa.Column('fact_count', sa.Integer(), nullable=False),
        sa.Column('provenance_urn', sa.String(255), nullable=False)
    )
    op.create_index('ix_attr_lineage_id_assessments', 'attribution_assessments', ['lineage_id'])
    op.create_index('ix_attr_assessment_id', 'attribution_assessments', ['assessment_id'])

    # 4. attribution_facts
    op.create_table(
        'attribution_facts',
        sa.Column('fact_id', sa.String(64), primary_key=True),
        sa.Column('assessment_id', sa.String(64), sa.ForeignKey('attribution_assessments.assessment_id', ondelete='CASCADE'), nullable=False),
        sa.Column('dimensions', JSONB, nullable=False)
    )
    op.create_index('ix_attr_assessment_id_facts', 'attribution_facts', ['assessment_id'])


def downgrade():
    op.drop_index('ix_attr_assessment_id_facts', table_name='attribution_facts')
    op.drop_table('attribution_facts')

    op.drop_index('ix_attr_assessment_id', table_name='attribution_assessments')
    op.drop_index('ix_attr_lineage_id_assessments', table_name='attribution_assessments')
    op.drop_table('attribution_assessments')

    op.drop_index('ix_attr_capability_id', table_name='attribution_lineage_nodes')
    op.drop_index('ix_attr_lineage_id_nodes', table_name='attribution_lineage_nodes')
    op.drop_table('attribution_lineage_nodes')

    op.drop_index('ix_attr_forecast_id', table_name='attribution_lineages')
    op.drop_index('ix_attr_lineage_decision_id', table_name='attribution_lineages')
    op.drop_table('attribution_lineages')
