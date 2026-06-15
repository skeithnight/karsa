"""regime engine init

Revision ID: 46_regime_engine_init
Revises: 45
Create Date: 2026-06-15 10:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '46_regime_engine_init'
down_revision = '45'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. regime_sessions
    op.create_table('regime_sessions',
        sa.Column('session_urn', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('aggregate_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('session_urn')
    )

    # 2. regime_snapshots (partitioned)
    op.execute("""
        CREATE TABLE regime_snapshots (
            snapshot_urn VARCHAR NOT NULL,
            segment_urn VARCHAR NOT NULL,
            horizon_urn VARCHAR NOT NULL,
            snapshot_date VARCHAR NOT NULL,
            regime_classification JSONB NOT NULL,
            confidence_score NUMERIC NOT NULL,
            regime_manifest_hash VARCHAR NOT NULL,
            evidence_manifest_hash VARCHAR NOT NULL,
            methodology_metadata JSONB NOT NULL,
            aggregate_version INTEGER NOT NULL,
            calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            PRIMARY KEY (snapshot_urn, calculated_at)
        ) PARTITION BY RANGE (calculated_at);
    """)

    # natural key unique constraint across the whole table isn't easily supported with partition ranges
    # unless partition key is part of it. We'll enforce at app level or uniquely inside partitions.
    # Actually, we can add a unique index if calculated_at is included, but we'll manage via code or add unique on (segment, horizon, date)
    op.execute("CREATE TABLE regime_snapshots_default PARTITION OF regime_snapshots DEFAULT;")
    op.execute("CREATE UNIQUE INDEX ix_regime_snapshots_nk ON regime_snapshots (segment_urn, horizon_urn, snapshot_date);")

    # 3. regime_transitions (partitioned)
    op.execute("""
        CREATE TABLE regime_transitions (
            transition_urn VARCHAR NOT NULL,
            from_regime JSONB NOT NULL,
            to_regime JSONB NOT NULL,
            transition_manifest_hash VARCHAR NOT NULL,
            supersedes_transition_urn VARCHAR,
            invalidates_transition_urn VARCHAR,
            aggregate_version INTEGER NOT NULL,
            transition_date TIMESTAMP WITH TIME ZONE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            PRIMARY KEY (transition_urn, transition_date)
        ) PARTITION BY RANGE (transition_date);
    """)

    op.execute("CREATE TABLE regime_transitions_default PARTITION OF regime_transitions DEFAULT;")

    # Immutability Triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION block_regime_snapshot_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'RegimeSnapshot is strictly immutable (DELETE blocked)';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF NEW.snapshot_urn != OLD.snapshot_urn OR
                   NEW.segment_urn != OLD.segment_urn OR
                   NEW.horizon_urn != OLD.horizon_urn OR
                   NEW.snapshot_date != OLD.snapshot_date OR
                   NEW.regime_manifest_hash != OLD.regime_manifest_hash OR
                   NEW.evidence_manifest_hash != OLD.evidence_manifest_hash THEN
                    RAISE EXCEPTION 'RegimeSnapshot immutable fields cannot be updated';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_block_regime_snapshot_mutation
        BEFORE UPDATE OR DELETE ON regime_snapshots
        FOR EACH ROW EXECUTE FUNCTION block_regime_snapshot_mutation();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION block_regime_transition_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'RegimeTransition is strictly immutable (DELETE blocked)';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF NEW.transition_urn != OLD.transition_urn OR
                   NEW.transition_manifest_hash != OLD.transition_manifest_hash THEN
                    RAISE EXCEPTION 'RegimeTransition immutable fields cannot be updated';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_block_regime_transition_mutation
        BEFORE UPDATE OR DELETE ON regime_transitions
        FOR EACH ROW EXECUTE FUNCTION block_regime_transition_mutation();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_block_regime_transition_mutation ON regime_transitions;")
    op.execute("DROP FUNCTION IF EXISTS block_regime_transition_mutation();")
    op.execute("DROP TRIGGER IF EXISTS trg_block_regime_snapshot_mutation ON regime_snapshots;")
    op.execute("DROP FUNCTION IF EXISTS block_regime_snapshot_mutation();")
    op.execute("DROP TABLE regime_transitions CASCADE;")
    op.execute("DROP TABLE regime_snapshots CASCADE;")
    op.drop_table('regime_sessions')
