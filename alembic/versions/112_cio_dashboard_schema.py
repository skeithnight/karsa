"""Sprint-59: CIO Dashboard — portfolio_snapshots and sector_exposures tables.

Revision ID: 112
Revises: 111
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "112_cio_dashboard_schema"
down_revision = "111_asset_risk_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Portfolio snapshots time-series
    op.create_table(
        "portfolio_snapshots",
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_equity", sa.Numeric(18, 4), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("gross_exposure", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_exposure", sa.Numeric(18, 4), nullable=False),
        sa.Column("daily_pnl", sa.Numeric(18, 4), nullable=False),
        sa.Column("max_drawdown_pct", sa.Numeric(10, 4), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 4), server_default="0"),
        sa.Column("unrealized_pnl", sa.Numeric(18, 4), server_default="0"),
        sa.Column("position_count", sa.Integer, server_default="0"),
    )

    # Try TimescaleDB hypertable, fall back to standard index
    try:
        op.execute("SELECT create_hypertable('portfolio_snapshots', 'snapshot_time')")
    except Exception:
        op.execute(
            "CREATE INDEX idx_portfolio_snapshots_time ON portfolio_snapshots (snapshot_time DESC)"
        )

    # Sector exposures time-series
    op.create_table(
        "sector_exposures",
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sector_name", sa.String(50), nullable=False),
        sa.Column("gross_exposure", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_exposure", sa.Numeric(18, 4), nullable=False),
    )

    try:
        op.execute("SELECT create_hypertable('sector_exposures', 'snapshot_time')")
    except Exception:
        op.execute(
            "CREATE INDEX idx_sector_exposures_time ON sector_exposures (snapshot_time DESC)"
        )

    # Composite index for latest sector query
    op.execute(
        "CREATE INDEX idx_sector_exposures_sector ON sector_exposures (sector_name, snapshot_time DESC)"
    )


def downgrade() -> None:
    op.drop_table("sector_exposures")
    op.drop_table("portfolio_snapshots")
