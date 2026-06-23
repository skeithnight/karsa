"""sprint52 data bridge dead letter table

Revision ID: 106
Revises: 105
Create Date: 2026-06-22

"""
from alembic import op

revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE data_bridge_dead_letter (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider_id UUID REFERENCES data_providers(id),
        raw_payload JSONB NOT NULL,
        error_message TEXT NOT NULL,
        error_type VARCHAR(50) NOT NULL,
        received_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    op.execute("""
    CREATE INDEX idx_dead_letter_received
    ON data_bridge_dead_letter (received_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS data_bridge_dead_letter;")
