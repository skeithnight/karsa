"""sprint05_allocation_views

Revision ID: da0ed664092f
Revises: 61
Create Date: 2026-06-19 23:35:20.889520

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da0ed664092f'
down_revision = '61'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE projection_worker_performance
        ADD COLUMN IF NOT EXISTS observation_count INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS current_drawdown NUMERIC DEFAULT 0,
        ADD COLUMN IF NOT EXISTS high_watermark NUMERIC DEFAULT 0;
    """)

    op.execute("""
    CREATE OR REPLACE VIEW vw_worker_eligibility AS
    SELECT 
        w.worker_urn,
        CASE 
            WHEN c.new_state = 'ACTIVE' THEN 'ALLOCATABLE'
            WHEN c.new_state = 'SUSPENDED' THEN 'BLOCKED'
            ELSE 'LIMITED'
        END AS eligibility_status
    FROM dim_worker w
    LEFT JOIN LATERAL (
        SELECT new_state FROM fact_capability_transition
        WHERE dim_worker_id = w.dim_worker_id
        ORDER BY event_sequence DESC LIMIT 1
    ) c ON true;
    """)

    op.execute("""
    CREATE OR REPLACE VIEW vw_allocation_readiness AS
    SELECT 
        e.worker_urn,
        e.eligibility_status,
        p.cumulative_gross_pnl AS cumulative_alpha,
        p.max_drawdown,
        p.observation_count
    FROM vw_worker_eligibility e
    LEFT JOIN projection_worker_performance p ON e.worker_urn = p.worker_id;
    """)

def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_allocation_readiness;")
    op.execute("DROP VIEW IF EXISTS vw_worker_eligibility;")
    op.execute("""
    ALTER TABLE projection_worker_performance
        DROP COLUMN IF EXISTS observation_count,
        DROP COLUMN IF EXISTS current_drawdown,
        DROP COLUMN IF EXISTS high_watermark;
    """)
