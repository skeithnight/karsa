"""Sprint-58: Live Risk — asset_risk_metrics table for volatility targeting.

Revision ID: 111
Revises: 110
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "111_asset_risk_metrics"
down_revision = "110_execution_bridge_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_risk_metrics",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("realized_volatility", sa.Numeric(10, 6), nullable=False),
        sa.Column("beta_to_spy", sa.Numeric(10, 4), nullable=True),
        sa.Column("var_95", sa.Numeric(18, 4), nullable=True),
        sa.Column("daily_vol_pct", sa.Numeric(10, 6), server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("symbol", "timeframe"),
    )

    # Index for latest volatility lookup
    op.execute(
        "CREATE INDEX idx_asset_risk_metrics_symbol ON asset_risk_metrics (symbol)"
    )


def downgrade() -> None:
    op.drop_table("asset_risk_metrics")
