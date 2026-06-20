"""add_post_mortem_records

Revision ID: 55_post_mortem_records_init
Revises: 54_market_structure
Create Date: 2026-06-18 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '55_post_mortem_records_init'
down_revision: Union[str, None] = '54_market_structure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS post_mortem_records (
        postmortem_id TEXT PRIMARY KEY,
        incident_ref TEXT UNIQUE NOT NULL,
        failure_classification JSONB NOT NULL,
        root_causes JSONB NOT NULL,
        findings JSONB NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    CREATE TABLE IF NOT EXISTS post_mortem_recommendations (
        recommendation_id TEXT PRIMARY KEY,
        postmortem_id TEXT NOT NULL,
        target_context TEXT NOT NULL,
        action_item TEXT NOT NULL,
        parameters JSONB NOT NULL,
        state TEXT NOT NULL,
        version INTEGER NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS post_mortem_recommendations;")
    op.execute("DROP TABLE IF EXISTS post_mortem_records;")
