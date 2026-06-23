class ProviderError(Exception):
    """Base class for all provider-related errors."""
    pass

class MissingCredentialsError(ProviderError):
    """Thrown when the provider is initialized with zero credentials."""
    pass

class AuthenticationError(ProviderError):
    """Thrown when credentials are provided but rejected by the API."""
    pass

class QuotaExhaustedError(ProviderError):
    """Thrown when all available keys have exhausted their quota."""
    pass

class RateLimitError(ProviderError):
    """Thrown when a key is temporarily rate-limited (e.g., 429 Too Many Requests)."""
    pass

class ProviderUnavailableError(ProviderError):
    """Thrown when the provider service is unreachable (e.g., 502, 503)."""
    pass

class TransientProviderError(ProviderError):
    """Thrown for other temporary network or provider anomalies."""
    pass


class LLMProviderExhaustedError(ProviderError):
    """Thrown when all providers in a model group have been exhausted."""
    pass
