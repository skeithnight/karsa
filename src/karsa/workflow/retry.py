import time
from typing import Callable, Any

class ProviderExhaustedException(Exception):
    pass

class RetryCoordinator:
    def __init__(self, max_attempts: int = 5, base_delay: int = 2):
        self.max_attempts = max_attempts
        self.base_delay = base_delay

    def execute_with_backoff(self, func: Callable[[], Any]) -> Any:
        from karsa.llm.errors import QuotaExhaustedError, RateLimitError, ProviderUnavailableError, TransientProviderError, MissingCredentialsError, AuthenticationError
        
        attempts = 0
        while attempts < self.max_attempts:
            try:
                return func()
            except (QuotaExhaustedError, RateLimitError, ProviderUnavailableError, TransientProviderError) as e:
                attempts += 1
                if attempts >= self.max_attempts:
                    raise ProviderExhaustedException(f"Failed after {self.max_attempts} attempts: {e}")
                delay = self.base_delay * (2 ** (attempts - 1))
                time.sleep(delay)
            except (MissingCredentialsError, AuthenticationError) as e:
                raise e # Fatal, no retry
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "timeout" in err_msg or "quota" in err_msg or "502" in err_msg or "503" in err_msg:
                    attempts += 1
                    if attempts >= self.max_attempts:
                        raise ProviderExhaustedException(f"Failed after {self.max_attempts} attempts: {e}")
                    delay = self.base_delay * (2 ** (attempts - 1))
                    time.sleep(delay)
                elif "api key not valid" in err_msg:
                    raise AuthenticationError(str(e))
                else:
                    raise e
        raise ProviderExhaustedException("Max attempts reached")
