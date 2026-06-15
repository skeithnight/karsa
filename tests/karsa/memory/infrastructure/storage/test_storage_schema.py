import pytest
from karsa.memory.infrastructure.storage.postgres_schema import get_all_migrations

def test_migrations_exist():
    migrations = get_all_migrations()
    assert len(migrations) == 3
    
    assert "snapshots_metadata" in migrations[0]
    assert "snapshot_lineage" in migrations[1]
    assert "schemas" in migrations[2]
