"""foundation remediation 2

Revision ID: 51_foundation_remediation
Revises: 50
Create Date: 2026-06-17 17:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '51_foundation_remediation'
down_revision = '50'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # event_journal modifications
    op.add_column('event_journal', sa.Column('aggregate_id', sa.String(length=255), nullable=True))
    op.add_column('event_journal', sa.Column('aggregate_type', sa.String(length=100), nullable=True))
    op.add_column('event_journal', sa.Column('event_id', sa.String(length=36), nullable=True))
    op.add_column('event_journal', sa.Column('schema_version', sa.Integer(), server_default='1', nullable=False))
    
    # Backfill missing defaults for existing rows (if any exist)
    op.execute("UPDATE event_journal SET aggregate_id = stream_id WHERE aggregate_id IS NULL")
    op.execute("UPDATE event_journal SET aggregate_type = 'Unknown' WHERE aggregate_type IS NULL")
    op.execute("UPDATE event_journal SET event_id = id::text WHERE event_id IS NULL")
    
    op.alter_column('event_journal', 'aggregate_id', nullable=False)
    op.alter_column('event_journal', 'aggregate_type', nullable=False)
    op.alter_column('event_journal', 'event_id', nullable=False)
    op.create_index(op.f('ix_event_journal_event_id'), 'event_journal', ['event_id'], unique=True)
    
    # event_outbox modifications
    op.add_column('event_outbox', sa.Column('event_id', sa.String(length=36), nullable=True))
    op.add_column('event_outbox', sa.Column('stream_id', sa.String(length=255), nullable=True))
    op.add_column('event_outbox', sa.Column('aggregate_type', sa.String(length=100), nullable=True))
    op.add_column('event_outbox', sa.Column('schema_version', sa.Integer(), server_default='1', nullable=False))
    
    op.execute("UPDATE event_outbox SET event_id = id::text WHERE event_id IS NULL")
    op.execute("UPDATE event_outbox SET stream_id = 'unknown' WHERE stream_id IS NULL")
    op.execute("UPDATE event_outbox SET aggregate_type = 'Unknown' WHERE aggregate_type IS NULL")
    
    op.alter_column('event_outbox', 'event_id', nullable=False)
    op.alter_column('event_outbox', 'stream_id', nullable=False)
    op.alter_column('event_outbox', 'aggregate_type', nullable=False)
    op.create_index(op.f('ix_event_outbox_event_id'), 'event_outbox', ['event_id'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_event_outbox_event_id'), table_name='event_outbox')
    op.drop_column('event_outbox', 'schema_version')
    op.drop_column('event_outbox', 'aggregate_type')
    op.drop_column('event_outbox', 'stream_id')
    op.drop_column('event_outbox', 'event_id')
    
    op.drop_index(op.f('ix_event_journal_event_id'), table_name='event_journal')
    op.drop_column('event_journal', 'schema_version')
    op.drop_column('event_journal', 'event_id')
    op.drop_column('event_journal', 'aggregate_type')
    op.drop_column('event_journal', 'aggregate_id')
