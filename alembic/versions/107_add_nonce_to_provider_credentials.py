"""audit fix: add nonce columns to provider_credentials

Revision ID: 107
Revises: 106
Create Date: 2026-06-22

"""
from alembic import op

revision = '107'
down_revision = '106'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE provider_credentials
    ADD COLUMN api_key_nonce TEXT NOT NULL DEFAULT '';
    """)
    op.execute("""
    ALTER TABLE provider_credentials
    ADD COLUMN api_secret_nonce TEXT;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE provider_credentials DROP COLUMN IF EXISTS api_secret_nonce;")
    op.execute("ALTER TABLE provider_credentials DROP COLUMN IF EXISTS api_key_nonce;")
