"""
Alembic migration for Sprint-15 Performance Engine Projections
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'sprint15_perf'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Context
    op.create_table('projection_decision_context',
        sa.Column('decision_id', sa.String(), primary_key=True),
        sa.Column('worker_id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('thesis_id', sa.String(), nullable=False),
        sa.Column('stated_confidence', sa.Numeric(), nullable=True),
        sa.Column('decision_timestamp', sa.DateTime(), nullable=False)
    )

    # Root append-only table
    op.create_table('projection_decision_performance',
        sa.Column('decision_id', sa.String(), nullable=False),
        sa.Column('outcome_sequence_id', sa.Integer(), nullable=False),
        sa.Column('attribution_generation', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('thesis_id', sa.String(), nullable=False),
        sa.Column('regime_id', sa.String(), nullable=True),
        sa.Column('gross_pnl', sa.Numeric(), nullable=False),
        sa.Column('net_pnl', sa.Numeric(), nullable=False),
        sa.Column('stated_confidence', sa.Numeric(), nullable=True),
        sa.Column('decision_timestamp', sa.DateTime(), nullable=False),
        sa.Column('projection_schema_version', sa.Integer(), nullable=False),
        sa.Column('calculation_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('decision_id', 'outcome_sequence_id', 'attribution_generation')
    )
    
    op.create_index('idx_perf_worker_date', 'projection_decision_performance', ['worker_id', sa.text('DATE(decision_timestamp)')])
    op.create_index('idx_perf_strategy_date', 'projection_decision_performance', ['strategy_id', sa.text('DATE(decision_timestamp)')])
    op.create_index('idx_perf_thesis_date', 'projection_decision_performance', ['thesis_id', sa.text('DATE(decision_timestamp)')])

    # Buckets
    op.create_table('projection_daily_pnl_bucket',
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', sa.String(), nullable=False),
        sa.Column('bucket_date', sa.Date(), nullable=False),
        sa.Column('daily_gross_pnl', sa.Numeric(), nullable=False),
        sa.Column('daily_net_pnl', sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint('target_type', 'target_id', 'bucket_date')
    )

    # Profiles (Abbreviated to essential fields for migration demonstration)
    for profile in ['worker', 'strategy', 'thesis', 'regime']:
        op.create_table(f'projection_{profile}_performance',
            sa.Column(f'{profile}_id', sa.String(), primary_key=True),
            sa.Column('cumulative_gross_pnl', sa.Numeric()),
            sa.Column('max_drawdown', sa.Numeric()),
            sa.Column('sharpe_proxy', sa.Numeric()),
            sa.Column('hit_rate', sa.Numeric())
        )
    
    op.create_table('projection_calibration',
        sa.Column('worker_id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('brier_score', sa.Numeric()),
        sa.PrimaryKeyConstraint('worker_id', 'strategy_id')
    )

    op.create_table('projection_performance_window',
        sa.Column('target_id', sa.String(), nullable=False),
        sa.Column('window_end', sa.Date(), nullable=False),
        sa.Column('window_size_days', sa.Integer(), nullable=False),
        sa.Column('rolling_gross_pnl', sa.Numeric()),
        sa.PrimaryKeyConstraint('target_id', 'window_end', 'window_size_days')
    )

    # Ranking View
    op.execute("""
        CREATE VIEW view_ranking_profile AS 
        SELECT worker_id, RANK() OVER (ORDER BY sharpe_proxy DESC) as rank 
        FROM projection_worker_performance
    """)

def downgrade():
    pass
