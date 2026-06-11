import time
from typing import Callable, Any

class ProviderExhaustedException(Exception):
    pass

class RetryCoordinator:
    def __init__(self, max_attempts: int = 5, base_delay: int = 2):
        self.max_attempts = max_attempts
        self.base_delay = base_delay

    def execute_with_backoff(self, func: Callable[[], Any]) -> Any:
        attempts = 0
        while attempts < self.max_attempts:
            try:
                return func()
            except Exception as e:
                err_msg = str(e).lower()
                # Simulate capturing transient faults like 429, 502, 503
                if "429" in err_msg or "timeout" in err_msg or "quota" in err_msg:
                    attempts += 1
                    if attempts >= self.max_attempts:
                        raise ProviderExhaustedException(f"Failed after {self.max_attempts} attempts: {e}")
                    delay = self.base_delay * (2 ** (attempts - 1))
                    time.sleep(delay)
                else:
                    # Semantic errors raise immediately
                    raise e
        raise ProviderExhaustedException("Max attempts reached")
