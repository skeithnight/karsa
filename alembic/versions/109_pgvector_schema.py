"""Sprint-54: pgvector schema for RAG institutional memory.

Revision ID: 109
Revises: 108
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "109_pgvector_schema"
down_revision = "108_llm_pool_config_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create ai_institutional_memory table
    op.create_table(
        "ai_institutional_memory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("reference_id", sa.String(36), nullable=False, index=True),
        sa.Column("ticker", sa.String(20), nullable=True, index=True),
        sa.Column("sector", sa.String(50), nullable=True, index=True),
        sa.Column("content_text", sa.Text, nullable=False),
        # embedding column uses pgvector type — created via raw SQL below
        sa.Column("embedding_model", sa.String(100), nullable=False, default="text-embedding-3-small"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add pgvector column (can't use SQLAlchemy for vector type)
    op.execute(
        "ALTER TABLE ai_institutional_memory ADD COLUMN embedding vector(1536) NOT NULL"
    )

    # Create HNSW index for fast cosine similarity search
    op.execute(
        "CREATE INDEX idx_ai_memory_embedding ON ai_institutional_memory "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # Composite index for filtered searches
    op.execute(
        "CREATE INDEX idx_ai_memory_ticker_event ON ai_institutional_memory "
        "(ticker, event_type) WHERE ticker IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_table("ai_institutional_memory")
    op.execute("DROP EXTENSION IF EXISTS vector")
