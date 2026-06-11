import pytest
import time
import os
from pathlib import Path
from karsa.llm.pool import ProviderPool, ProviderKey

def test_provider_pool_rotation(tmp_path: Path):
    registry = tmp_path / "registry.json"
    keys = ["key1", "key2"]
    pool = ProviderPool("gemini", keys, registry)
    
    # Round robin
    k1 = pool.get_next_key()
    assert k1.key == "key1"
    
    k2 = pool.get_next_key()
    assert k2.key == "key2"
    
    k3 = pool.get_next_key()
    assert k3.key == "key1"

def test_provider_pool_quota_exhaustion_and_recovery(tmp_path: Path):
    os.environ["KARSA_TESTING"] = "1"
    registry = tmp_path / "registry.json"
    keys = ["key1"]
    pool = ProviderPool("gemini", keys, registry)
    
    k1 = pool.get_next_key()
    pool.mark_failure(k1, is_quota=True)
    
    # Should be suspended
    assert k1.status == "SUSPENDED"
    assert pool.get_next_key() is None
    
    # Wait for recovery (in tests delay is 0.1s)
    time.sleep(0.15)
    
    # Should recover
    k_recovered = pool.get_next_key()
    assert k_recovered is not None
    assert k_recovered.status == "ACTIVE"
    assert k_recovered.quota_failures == 0

def test_provider_registry_persistence(tmp_path: Path):
    registry = tmp_path / "registry.json"
    keys = ["key1", "key2"]
    pool1 = ProviderPool("gemini", keys, registry)
    
    k1 = pool1.get_next_key()
    pool1.mark_success(k1)
    pool1.mark_failure(pool1.keys[1], is_quota=True)
    
    pool2 = ProviderPool("gemini", keys, registry)
    assert pool2.keys[0].total_requests == 1
    assert pool2.keys[1].status == "SUSPENDED"
    assert pool2.keys[1].quota_failures == 1
