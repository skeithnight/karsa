"""sprint52 wave1 remediation

Revision ID: 49_wave1_remediation
Revises: 48
Create Date: 2026-06-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '49_wave1_remediation'
down_revision = '48'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Event Journal
    op.drop_table('event_journal')
    op.create_table('event_journal',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('sequence_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('stream_id', sa.String(length=255), nullable=False),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('sequence_id'),
        sa.UniqueConstraint('stream_id', 'stream_version', name='uq_event_journal_stream_version')
    )
    op.create_index(op.f('ix_event_journal_stream_id'), 'event_journal', ['stream_id'], unique=False)

    # Event Outbox
    op.create_table('event_outbox',
        sa.Column('id', sa.CHAR(length=32), nullable=False),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('published', sa.Integer(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_outbox_published'), 'event_outbox', ['published'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_event_outbox_published'), table_name='event_outbox')
    op.drop_table('event_outbox')
    op.drop_index(op.f('ix_event_journal_stream_id'), table_name='event_journal')
    op.drop_table('event_journal')
