CREATE_SNAPSHOTS_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots_metadata (
    id VARCHAR(255) PRIMARY KEY,
    namespace VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    provenance_reason TEXT,
    payload_hash VARCHAR(255) NOT NULL,
    schema_id VARCHAR(255) NOT NULL,
    importance_tier VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_namespace ON snapshots_metadata(namespace);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON snapshots_metadata(created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_hash ON snapshots_metadata(payload_hash);
"""

CREATE_SNAPSHOT_LINEAGE_TABLE = """
CREATE TABLE IF NOT EXISTS snapshot_lineage (
    source_id VARCHAR(255) NOT NULL,
    target_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL,
    PRIMARY KEY (source_id, target_id, relationship_type),
    FOREIGN KEY (source_id) REFERENCES snapshots_metadata(id),
    FOREIGN KEY (target_id) REFERENCES snapshots_metadata(id)
);
"""

CREATE_SCHEMAS_TABLE = """
CREATE TABLE IF NOT EXISTS schemas (
    schema_id VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    json_schema JSONB NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (schema_id, version)
);
"""

def get_all_migrations() -> list[str]:
    return [
        CREATE_SNAPSHOTS_METADATA_TABLE,
        CREATE_SNAPSHOT_LINEAGE_TABLE,
        CREATE_SCHEMAS_TABLE,
    ]
