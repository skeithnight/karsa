import pytest
from karsa.llm.client import LLMClient
from karsa.llm.provider import ProviderManager, ProviderRetryPolicy
import os
from pathlib import Path

class FailingMockClient(LLMClient):
    def __init__(self, name: str, fails_before_success: int):
        super().__init__()
        self.model_name = name
        self.fails_before_success = fails_before_success
        self.attempts = 0
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.attempts += 1
        if self.attempts <= self.fails_before_success:
            raise Exception("503 UNAVAILABLE")
        return f"Success from {self.model_name}"

def test_scenario_a_retry_success(tmp_path: Path):
    os.environ["KARSA_TESTING"] = "1"
    obs = ObservabilityManager(tmp_path)
    client = FailingMockClient("test-1", 2)
    provider = ProviderManager([client], obs_manager=obs)
    
    response = provider.generate_with_obs("Agent", "test")
    assert response == "Success from test-1"
    assert provider.total_retries == 2
    assert provider.total_fallbacks == 0
    assert client.attempts == 3

def test_scenario_b_fallback(tmp_path: Path):
    os.environ["KARSA_TESTING"] = "1"
    obs = ObservabilityManager(tmp_path)
    # primary fails 4 times (max attempts is 4, so it fails 4 times then falls back)
    client1 = FailingMockClient("primary", 10)
    # secondary succeeds on first try
    client2 = FailingMockClient("secondary", 0)
    
    provider = ProviderManager([client1, client2], obs_manager=obs)
    
    response = provider.generate_with_obs("Agent", "test")
    assert response == "Success from secondary"
    assert provider.total_retries == 3 # 3 retries (attempt 1,2,3,4 -> 3 retries)
    assert provider.total_fallbacks == 1
    assert client1.attempts == 4
    assert client2.attempts == 1
    assert provider.model_name == "secondary"

def test_scenario_c_all_fail(tmp_path: Path):
    os.environ["KARSA_TESTING"] = "1"
    obs = ObservabilityManager(tmp_path)
    client1 = FailingMockClient("primary", 10)
    client2 = FailingMockClient("secondary", 10)
    
    provider = ProviderManager([client1, client2], obs_manager=obs)
    
    with pytest.raises(Exception) as excinfo:
        provider.generate_with_obs("Agent", "test")
        
    assert "All providers failed. Last error: 503 UNAVAILABLE" in str(excinfo.value)
    assert provider.total_fallbacks == 1
    # 3 retries for primary, 3 retries for secondary = 6 total retries
    assert provider.total_retries == 6 
