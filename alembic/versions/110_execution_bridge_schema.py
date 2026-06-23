"""Sprint-56: Execution Bridge schema — orders, fills, risk limits.

Revision ID: 110
Revises: 109
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "110_execution_bridge_schema"
down_revision = "109_pgvector_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(100), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("target_quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(18, 8), server_default="0"),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("status", sa.String(20), server_default="PENDING", index=True),
        sa.Column("broker_order_id", sa.String(100), nullable=True, index=True),
        sa.Column("parent_order_id", sa.String(36), nullable=True, index=True),
        sa.Column("is_twap_child", sa.Boolean, server_default="false"),
        sa.Column("twap_sequence", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "execution_fills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("execution_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("broker_fill_id", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("fill_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("commission", sa.Numeric(18, 4), server_default="0"),
        sa.Column("filled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "execution_risk_limits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("limit_type", sa.String(50), unique=True, nullable=False),
        sa.Column("limit_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
    )

    # Seed default risk limits
    op.execute("""
        INSERT INTO execution_risk_limits (id, limit_type, limit_value, is_active) VALUES
        ('00000000-0000-0000-0000-000000000001', 'MAX_SINGLE_ORDER_USD', 500000, true),
        ('00000000-0000-0000-0000-000000000002', 'MAX_POSITION_SIZE_PCT', 5.0, true),
        ('00000000-0000-0000-0000-000000000003', 'MAX_DAILY_TURNOVER_USD', 5000000, true)
    """)


def downgrade() -> None:
    op.drop_table("execution_fills")
    op.drop_table("execution_orders")
    op.drop_table("execution_risk_limits")
