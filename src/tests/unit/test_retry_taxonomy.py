import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from karsa.llm.errors import (
    MissingCredentialsError,
    AuthenticationError,
    QuotaExhaustedError,
    RateLimitError,
    ProviderUnavailableError,
    TransientProviderError
)
from karsa.llm.pool import ProviderPool
from karsa.workflow.retry import RetryCoordinator, ProviderExhaustedException

def test_pool_missing_credentials_throws():
    with patch("os.environ.get", return_value=None):
        with pytest.raises(MissingCredentialsError):
            ProviderPool("gemini", [], Path("dummy.json"))

def test_missing_credentials_zero_retries():
    coordinator = RetryCoordinator(max_attempts=3, base_delay=0)
    
    attempts = 0
    def mock_call():
        nonlocal attempts
        attempts += 1
        raise MissingCredentialsError("No keys")

    with pytest.raises(MissingCredentialsError):
        coordinator.execute_with_backoff(mock_call)
        
    assert attempts == 1

def test_auth_failure_immediate():
    coordinator = RetryCoordinator(max_attempts=3, base_delay=0)
    
    attempts = 0
    def mock_call():
        nonlocal attempts
        attempts += 1
        raise AuthenticationError("Invalid key")

    with pytest.raises(AuthenticationError):
        coordinator.execute_with_backoff(mock_call)
        
    assert attempts == 1

def test_quota_exhausted_retries():
    coordinator = RetryCoordinator(max_attempts=3, base_delay=0)
    
    attempts = 0
    def mock_call():
        nonlocal attempts
        attempts += 1
        raise QuotaExhaustedError("Quota out")

    with pytest.raises(ProviderExhaustedException):
        with patch("time.sleep"):
            coordinator.execute_with_backoff(mock_call)
        
    assert attempts == 3

def test_transient_provider_failure_retries():
    coordinator = RetryCoordinator(max_attempts=3, base_delay=0)
    
    attempts = 0
    def mock_call():
        nonlocal attempts
        attempts += 1
        raise ProviderUnavailableError("502 Bad Gateway")

    with pytest.raises(ProviderExhaustedException):
        with patch("time.sleep"):
            coordinator.execute_with_backoff(mock_call)
        
    assert attempts == 3
