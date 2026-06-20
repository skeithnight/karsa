"""review and attribution tables

Revision ID: 005_review_attr
Revises: 004_thesis_intelligence_read_models
Create Date: 2026-06-19 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_review_attr'
down_revision = '004_thesis_intelligence_read_models'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Review Tables
    op.create_table(
        'review_snapshots',
        sa.Column('review_urn', sa.String(255), primary_key=True),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_urn', sa.String(255), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('lineage_type', sa.String(50), nullable=True),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('review_urn', 'stream_version', name='uq_review_snapshots_version')
    )
    
    op.create_index('ix_review_snapshots_target', 'review_snapshots', ['target_urn'])

    op.create_table(
        'assumption_grades',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('review_urn', sa.String(255), nullable=False),
        sa.Column('assumption_urn', sa.String(255), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.UniqueConstraint('review_urn', 'assumption_urn', 'stream_version', name='uq_assumption_grades_version')
    )

    op.create_table(
        'calibration_snapshots',
        sa.Column('review_urn', sa.String(255), primary_key=True),
        sa.Column('stated_confidence', sa.Float(), nullable=False),
        sa.Column('actual_accuracy', sa.Float(), nullable=False),
        sa.Column('calibration_delta', sa.Float(), nullable=False),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.UniqueConstraint('review_urn', 'stream_version', name='uq_calibration_snapshots_version')
    )

    # Attribution Tables
    op.create_table(
        'attribution_snapshots',
        sa.Column('attribution_urn', sa.String(255), primary_key=True),
        sa.Column('review_urn', sa.String(255), nullable=False),
        sa.Column('benchmark_urn', sa.String(255), nullable=False),
        sa.Column('absolute_return', sa.Float(), nullable=False),
        sa.Column('benchmark_return', sa.Float(), nullable=False),
        sa.Column('true_alpha', sa.Float(), nullable=False),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.UniqueConstraint('attribution_urn', 'stream_version', name='uq_attribution_snapshots_version')
    )

    op.create_table(
        'attribution_nodes',
        sa.Column('node_id', sa.String(255), primary_key=True),
        sa.Column('attribution_urn', sa.String(255), nullable=False),
        sa.Column('parent_node_id', sa.String(255), nullable=True),
        sa.Column('subject_type', sa.String(50), nullable=False),
        sa.Column('subject_urn', sa.String(255), nullable=False),
        sa.Column('skill_ratio', sa.Float(), nullable=False),
        sa.Column('luck_ratio', sa.Float(), nullable=False),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        # Unique constraint removed because multiple nodes could have same stream_version in same attribution, but node_id is PK.
    )

    op.create_index('ix_attribution_nodes_attr', 'attribution_nodes', ['attribution_urn'])
    op.create_index('ix_attribution_nodes_subject', 'attribution_nodes', ['subject_urn'])


def downgrade() -> None:
    op.drop_table('attribution_nodes')
    op.drop_table('attribution_snapshots')
    op.drop_table('calibration_snapshots')
    op.drop_table('assumption_grades')
    op.drop_table('review_snapshots')
