"""
Alembic migration for Sprint-37 Decision Journal Foundation
"""
from alembic import op
import sqlalchemy as sa

revision = '37_decision_journal_init'
down_revision = 'sprint15_perf'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create partition tables and active_leaf_projections
    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_journals (
            decision_id VARCHAR(128) NOT NULL,
            parent_decision_id VARCHAR(128),
            root_decision_id VARCHAR(128) NOT NULL,
            proposing_agent_id VARCHAR(128) NOT NULL,
            signature VARCHAR(256) NOT NULL,
            thesis_urn VARCHAR(128) NOT NULL,
            context_hash VARCHAR(64) NOT NULL,
            context_uri VARCHAR(512) NOT NULL,
            context_snapshot_json JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (decision_id, root_decision_id, created_at)
        ) PARTITION BY RANGE (created_at);
        
        CREATE TABLE IF NOT EXISTS decision_revisions (
            revision_id VARCHAR(128) NOT NULL,
            parent_decision_id VARCHAR(128) NOT NULL,
            root_decision_id VARCHAR(128) NOT NULL,
            proposing_agent_id VARCHAR(128) NOT NULL,
            signature VARCHAR(256) NOT NULL,
            correction_reason VARCHAR(512) NOT NULL,
            context_hash VARCHAR(64) NOT NULL,
            context_uri VARCHAR(512) NOT NULL,
            context_snapshot_json JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (revision_id, root_decision_id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE TABLE IF NOT EXISTS decision_evidences (
            evidence_id VARCHAR(128) NOT NULL,
            decision_id VARCHAR(128) NOT NULL,
            attached_by_agent_id VARCHAR(128) NOT NULL,
            signature VARCHAR(256) NOT NULL,
            evidence_json JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (evidence_id, created_at)
        ) PARTITION BY RANGE (created_at);

        CREATE TABLE IF NOT EXISTS active_leaf_projections (
            root_decision_id VARCHAR(128) PRIMARY KEY,
            active_leaf_decision_id VARCHAR(128) NOT NULL,
            version INTEGER NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Add immutability triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION block_journal_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Decision Journal records are strictly immutable. UPDATE and DELETE operations are prohibited.';
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS enforce_journal_immutability ON decision_journals;
        CREATE TRIGGER enforce_journal_immutability
        BEFORE UPDATE OR DELETE ON decision_journals
        FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();

        DROP TRIGGER IF EXISTS enforce_revision_immutability ON decision_revisions;
        CREATE TRIGGER enforce_revision_immutability
        BEFORE UPDATE OR DELETE ON decision_revisions
        FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();

        DROP TRIGGER IF EXISTS enforce_evidence_immutability ON decision_evidences;
        CREATE TRIGGER enforce_evidence_immutability
        BEFORE UPDATE OR DELETE ON decision_evidences
        FOR EACH ROW EXECUTE FUNCTION block_journal_mutation();
    """)

def downgrade():
    op.execute("""
        DROP TRIGGER IF EXISTS enforce_journal_immutability ON decision_journals;
        DROP TRIGGER IF EXISTS enforce_revision_immutability ON decision_revisions;
        DROP TRIGGER IF EXISTS enforce_evidence_immutability ON decision_evidences;
        DROP FUNCTION IF EXISTS block_journal_mutation();
        DROP TABLE IF EXISTS active_leaf_projections CASCADE;
        DROP TABLE IF EXISTS decision_evidences CASCADE;
        DROP TABLE IF EXISTS decision_revisions CASCADE;
        DROP TABLE IF EXISTS decision_journals CASCADE;
    """)
