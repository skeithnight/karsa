import os
import pytest
from pathlib import Path
from karsa.llm.pool import ProviderPool

@pytest.fixture
def clean_env(monkeypatch):
    for key in list(os.environ.keys()):
        if "GEMINI" in key or "GOOGLE" in key or "KARSA" in key:
            monkeypatch.delenv(key, raising=False)
    yield monkeypatch

def test_empty_environment(clean_env):
    pool = ProviderPool("gemini", [], Path("dummy.json"))
    assert len(pool.keys) == 0

def test_gemini_api_key(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "key1")
    pool = ProviderPool("gemini", [], Path("dummy.json"))
    assert len(pool.keys) == 1
    assert pool.keys[0].key == "key1"

def test_google_api_key(clean_env):
    clean_env.setenv("GOOGLE_API_KEY", "key_google")
    pool = ProviderPool("gemini", [], Path("dummy.json"))
    assert len(pool.keys) == 1
    assert pool.keys[0].key == "key_google"

def test_karsa_gemini_keys_comma_separated(clean_env):
    clean_env.setenv("KARSA_GEMINI_KEYS", "k1, k2 ,k3")
    pool = ProviderPool("gemini", [], Path("dummy.json"))
    assert len(pool.keys) == 3
    extracted_keys = {k.key for k in pool.keys}
    assert extracted_keys == {"k1", "k2", "k3"}

def test_gemini_api_key_indexed(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "idx1")
    clean_env.setenv("GEMINI_API_KEY_2", "idx2")
    pool = ProviderPool("gemini", [], Path("dummy.json"))
    assert len(pool.keys) == 2
    extracted_keys = {k.key for k in pool.keys}
    assert extracted_keys == {"idx1", "idx2"}

def test_duplicate_keys_removed(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "dup_key")
    clean_env.setenv("GOOGLE_API_KEY", "dup_key")
    clean_env.setenv("KARSA_GEMINI_KEYS", "dup_key, other_key, dup_key")
    clean_env.setenv("GEMINI_API_KEY_1", "other_key")
    pool = ProviderPool("gemini", [], Path("dummy.json"))
    
    assert len(pool.keys) == 2
    extracted_keys = {k.key for k in pool.keys}
    assert extracted_keys == {"dup_key", "other_key"}
