"""portfolio_read_models_and_event_journal

Revision ID: 48
Revises: 47
Create Date: 2026-06-16 23:11:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '48'
down_revision = '47'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Phase 1: Event Journal
    op.create_table(
        'event_journal',
        sa.Column('global_sequence', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(), nullable=False, unique=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('aggregate_type', sa.String(), nullable=False),
        sa.Column('aggregate_id', sa.String(), nullable=False),
        sa.Column('aggregate_version', sa.Integer(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=False)
    )

    # Phase 2: Projection Checkpoints
    op.create_table(
        'projection_checkpoints',
        sa.Column('projection_name', sa.String(), primary_key=True),
        sa.Column('last_processed_sequence', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default='NOT_STARTED'),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    # Phase 3: Portfolio Read Models
    op.create_table(
        'portfolio_read_valuations',
        sa.Column('portfolio_id', sa.String(), primary_key=True),
        sa.Column('net_asset_value', sa.Float(), nullable=False),
        sa.Column('cash_balance', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    op.create_table(
        'portfolio_read_positions',
        sa.Column('asset_id', sa.String(), primary_key=True),
        sa.Column('portfolio_id', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('average_cost', sa.Float(), nullable=False),
        sa.Column('market_value', sa.Float(), nullable=False),
        sa.Column('exposure_pct', sa.Float(), nullable=False),
        sa.Column('exposure_value', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    op.create_table(
        'portfolio_read_cash_ledgers',
        sa.Column('portfolio_id', sa.String(), primary_key=True),
        sa.Column('balance', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('portfolio_read_cash_ledgers')
    op.drop_table('portfolio_read_positions')
    op.drop_table('portfolio_read_valuations')
    op.drop_table('projection_checkpoints')
    op.drop_table('event_journal')
