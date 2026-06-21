"""sprint09 attribution projections

Revision ID: 97
Revises: 96
Create Date: 2026-06-20

"""
from alembic import op

revision = '97'
down_revision = '96'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Worker attribution projection (derived, mutable)
    op.execute("""
    CREATE TABLE worker_attribution_projection (
        target_urn VARCHAR(256) PRIMARY KEY,
        total_attributions INTEGER NOT NULL DEFAULT 0,
        avg_quality_score NUMERIC(5,4) NOT NULL DEFAULT 0,
        total_contribution_bps NUMERIC(12,4) NOT NULL DEFAULT 0,
        last_attributed TIMESTAMPTZ
    );
    """)

    # Thesis attribution projection (derived, mutable)
    op.execute("""
    CREATE TABLE thesis_attribution_projection (
        thesis_urn VARCHAR(256) PRIMARY KEY,
        total_attributions INTEGER NOT NULL DEFAULT 0,
        avg_quality_score NUMERIC(5,4) NOT NULL DEFAULT 0,
        last_attributed TIMESTAMPTZ
    );
    """)

    # Regime attribution projection (derived, mutable)
    op.execute("""
    CREATE TABLE regime_attribution_projection (
        regime_id VARCHAR(64) PRIMARY KEY,
        total_evaluations INTEGER NOT NULL DEFAULT 0,
        avg_regime_effect_bps NUMERIC(12,4) NOT NULL DEFAULT 0,
        last_attributed TIMESTAMPTZ
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS regime_attribution_projection;")
    op.execute("DROP TABLE IF EXISTS thesis_attribution_projection;")
    op.execute("DROP TABLE IF EXISTS worker_attribution_projection;")
