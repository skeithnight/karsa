"""Thesis Evolution Engine Initialization

Revision ID: 47
Revises: 46
Create Date: 2026-06-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '47'
down_revision = '46_regime_engine_init'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Theses Table
    op.execute("""
        CREATE TABLE theses (
            thesis_urn TEXT PRIMARY KEY,
            current_snapshot_urn TEXT NOT NULL,
            current_status TEXT NOT NULL,
            aggregate_version INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
        CREATE INDEX idx_theses_status ON theses (current_status, thesis_urn);
        CREATE INDEX idx_theses_current_snapshot ON theses (current_snapshot_urn);
    """)

    # 2. Thesis Snapshots (Partitioned)
    op.execute("""
        CREATE TABLE thesis_snapshots (
            snapshot_urn TEXT NOT NULL,
            thesis_urn TEXT NOT NULL,
            snapshot_version INTEGER NOT NULL,
            snapshot_state TEXT NOT NULL,
            origin_regime_snapshot_urn TEXT NOT NULL,
            supersedes_snapshot_urn TEXT,
            invalidates_snapshot_urn TEXT,
            thesis_manifest_hash TEXT NOT NULL,
            evidence_manifest_hash TEXT NOT NULL,
            assumption_manifest_hash TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            PRIMARY KEY (snapshot_urn, created_at),
            FOREIGN KEY (thesis_urn) REFERENCES theses(thesis_urn)
        ) PARTITION BY RANGE (created_at);
        
        CREATE TABLE thesis_snapshots_y2026m06 PARTITION OF thesis_snapshots
            FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
        CREATE TABLE thesis_snapshots_y2026m07 PARTITION OF thesis_snapshots
            FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

        CREATE INDEX idx_snapshot_thesis ON thesis_snapshots (thesis_urn);
        CREATE INDEX idx_snapshot_supersedes ON thesis_snapshots (supersedes_snapshot_urn);
    """)

    # 3. Thesis Transitions
    op.execute("""
        CREATE TABLE thesis_transitions (
            transition_urn TEXT PRIMARY KEY,
            thesis_urn TEXT NOT NULL,
            supersedes_transition_urn TEXT,
            delta_manifest_hash TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            FOREIGN KEY (thesis_urn) REFERENCES theses(thesis_urn)
        );
        CREATE INDEX idx_transition_thesis ON thesis_transitions (thesis_urn);
        CREATE INDEX idx_transition_supersedes ON thesis_transitions (supersedes_transition_urn);
    """)

    # 4. Thesis Assumption Identities
    op.execute("""
        CREATE TABLE thesis_assumption_identities (
            assumption_urn TEXT PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
    """)

    # 5. Thesis Assumption Versions
    op.execute("""
        CREATE TABLE thesis_assumption_versions (
            assumption_urn TEXT NOT NULL,
            assumption_version INTEGER NOT NULL,
            lifecycle_state TEXT NOT NULL,
            raw_confidence REAL NOT NULL,
            assumption_manifest_hash TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            PRIMARY KEY (assumption_urn, assumption_version),
            FOREIGN KEY (assumption_urn) REFERENCES thesis_assumption_identities(assumption_urn)
        );
        CREATE INDEX idx_assumption_identity ON thesis_assumption_versions (assumption_urn);
    """)

    # 6. Thesis Deltas
    op.execute("""
        CREATE TABLE thesis_deltas (
            delta_urn TEXT PRIMARY KEY,
            transition_urn TEXT NOT NULL,
            delta_manifest_hash TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            FOREIGN KEY (transition_urn) REFERENCES thesis_transitions(transition_urn)
        );
    """)

    # 7. Assumption Outcome References
    op.execute("""
        CREATE TABLE assumption_outcome_references (
            reference_urn TEXT PRIMARY KEY,
            assumption_urn TEXT NOT NULL,
            attribution_reference_urn TEXT NOT NULL,
            review_reference_urn TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            FOREIGN KEY (assumption_urn) REFERENCES thesis_assumption_identities(assumption_urn)
        );
    """)

    # Triggers for Immutability
    op.execute("""
        CREATE OR REPLACE FUNCTION block_thesis_snapshot_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ImmutableMutationError: thesis_snapshots cannot be modified or deleted';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER tg_block_thesis_snapshot_mutation
        BEFORE UPDATE OR DELETE ON thesis_snapshots
        FOR EACH ROW EXECUTE FUNCTION block_thesis_snapshot_mutation();
        
        CREATE OR REPLACE FUNCTION block_thesis_transition_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ImmutableMutationError: thesis_transitions cannot be modified or deleted';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER tg_block_thesis_transition_mutation
        BEFORE UPDATE OR DELETE ON thesis_transitions
        FOR EACH ROW EXECUTE FUNCTION block_thesis_transition_mutation();
        
        CREATE OR REPLACE FUNCTION block_thesis_delta_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ImmutableMutationError: thesis_deltas cannot be modified or deleted';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER tg_block_thesis_delta_mutation
        BEFORE UPDATE OR DELETE ON thesis_deltas
        FOR EACH ROW EXECUTE FUNCTION block_thesis_delta_mutation();
    """)


def downgrade() -> None:
    # Drop Triggers and Functions
    op.execute("""
        DROP TRIGGER IF EXISTS tg_block_thesis_delta_mutation ON thesis_deltas;
        DROP FUNCTION IF EXISTS block_thesis_delta_mutation();
        
        DROP TRIGGER IF EXISTS tg_block_thesis_transition_mutation ON thesis_transitions;
        DROP FUNCTION IF EXISTS block_thesis_transition_mutation();
        
        DROP TRIGGER IF EXISTS tg_block_thesis_snapshot_mutation ON thesis_snapshots;
        DROP FUNCTION IF EXISTS block_thesis_snapshot_mutation();
    """)
    
    # Drop Tables
    op.execute("DROP TABLE IF EXISTS assumption_outcome_references;")
    op.execute("DROP TABLE IF EXISTS thesis_deltas;")
    op.execute("DROP TABLE IF EXISTS thesis_assumption_versions;")
    op.execute("DROP TABLE IF EXISTS thesis_assumption_identities;")
    op.execute("DROP TABLE IF EXISTS thesis_transitions;")
    op.execute("DROP TABLE IF EXISTS thesis_snapshots;")
    op.execute("DROP TABLE IF EXISTS theses;")
