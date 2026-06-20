"""Sprint 50 Thesis Enrichment"""

def upgrade():
    # Execute raw DDL
    ddl = '''
    CREATE TABLE IF NOT EXISTS thesis_snapshots (
        snapshot_urn VARCHAR PRIMARY KEY,
        snapshot_version INT NOT NULL,
        lifecycle_state VARCHAR NOT NULL,
        origin_regime_snapshot_urn VARCHAR,
        supersedes_snapshot_urn VARCHAR,
        invalidates_snapshot_urn VARCHAR
    );
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS thesis_urn VARCHAR;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS title VARCHAR;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS summary TEXT;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS rationale TEXT;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS confidence NUMERIC;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS author_urn VARCHAR;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS regime_urn VARCHAR;
    ALTER TABLE thesis_snapshots ADD COLUMN IF NOT EXISTS assumptions_jsonb JSONB;
def downgrade():
    ddl = '''
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS assumptions_jsonb;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS regime_urn;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS author_urn;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS confidence;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS rationale;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS summary;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS title;
    ALTER TABLE thesis_snapshots DROP COLUMN IF EXISTS thesis_urn;
    '''
    # Note: we don't drop the table if it was there before, 
    # but we drop the columns we added.
