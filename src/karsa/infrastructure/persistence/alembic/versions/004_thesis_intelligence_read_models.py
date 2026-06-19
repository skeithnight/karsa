"""thesis intelligence read models

Revision ID: 004_thesis_intelligence_read_models
Revises: 003_thesis_enrichment
Create Date: 2026-06-19 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_thesis_intelligence_read_models'
down_revision: Union[str, None] = '003_thesis_enrichment'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # thesis_timeline
    op.create_table(
        'thesis_timeline',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('thesis_urn', sa.String(255), nullable=False, index=True),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.Column('causation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_urn', sa.String(255), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(255), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('thesis_urn', 'stream_version', name='uq_thesis_timeline_version')
    )

    # confidence_history
    op.create_table(
        'confidence_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('thesis_urn', sa.String(255), nullable=False, index=True),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.Column('previous_confidence', sa.Float(), nullable=False),
        sa.Column('new_confidence', sa.Float(), nullable=False),
        sa.Column('delta', sa.Float(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(255), nullable=False),
        sa.Column('causation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('thesis_urn', 'stream_version', name='uq_confidence_history_version')
    )

    # assumption_snapshots
    op.create_table(
        'assumption_snapshots',
        sa.Column('assumption_urn', sa.String(255), primary_key=True),
        sa.Column('thesis_urn', sa.String(255), nullable=False, index=True),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('challenge_count', sa.Integer(), nullable=False, server_default='0')
    )

    # assumption_timeline
    op.create_table(
        'assumption_timeline',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('assumption_urn', sa.String(255), nullable=False, index=True),
        sa.Column('event_type', sa.String(255), nullable=False),
        sa.Column('actor_urn', sa.String(255), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('assumption_urn', 'event_id', name='uq_assumption_timeline_event')
    )

    # thesis_health_snapshots
    op.create_table(
        'thesis_health_snapshots',
        sa.Column('thesis_urn', sa.String(255), primary_key=True),
        sa.Column('lifecycle_state', sa.String(255), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('total_assumptions', sa.Integer(), nullable=False),
        sa.Column('valid_assumptions', sa.Integer(), nullable=False),
        sa.Column('challenged_assumptions', sa.Integer(), nullable=False),
        sa.Column('invalid_assumptions', sa.Integer(), nullable=False),
        sa.Column('health_score', sa.Float(), nullable=False),
        sa.Column('health_status', sa.String(50), nullable=False),
        sa.Column('snapshot_version', sa.Integer(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('thesis_health_snapshots')
    op.drop_table('assumption_timeline')
    op.drop_table('assumption_snapshots')
    op.drop_table('confidence_history')
    op.drop_table('thesis_timeline')
