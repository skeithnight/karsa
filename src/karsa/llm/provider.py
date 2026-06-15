import time
from typing import List
from karsa.llm.client import LLMClient


class ProviderRetryPolicy:
    def __init__(self, max_attempts=4):
        self.max_attempts = max_attempts
        
    def should_retry(self, exception: Exception) -> bool:
        error_msg = str(exception).lower()
        retryable_keywords = ["429", "500", "502", "503", "504", "timeout", "connection error", "unavailable"]
        for kw in retryable_keywords:
            if kw in error_msg:
                return True
        return False
        
    def get_backoff_seconds(self, attempt: int) -> int:
        if attempt == 1:
            return 5
        elif attempt == 2:
            return 10
        elif attempt == 3:
            return 20
        return 0

class ProviderManager(LLMClient):
    def __init__(self, providers: List[LLMClient], retry_policy: ProviderRetryPolicy = None):
        super().__init__()
        if not providers:
            raise ValueError("Must provide at least one LLMClient")
        self.providers = providers
        self.retry_policy = retry_policy or ProviderRetryPolicy()
        self.current_provider_index = 0
        
        self.total_retries = 0
        self.total_fallbacks = 0
        self.last_error = "None"
        self.last_failure_timestamp = "N/A"
        
    @property
    def model_name(self):
        if self.current_provider_index < len(self.providers):
            return self.providers[self.current_provider_index].model_name
        return "ALL_FAILED"
        
    @property
    def current_key(self):
        if self.current_provider_index < len(self.providers):
            return getattr(self.providers[self.current_provider_index], "current_key_fingerprint", "mock")
        return "none"
        
    @property
    def quota_failures(self):
        if self.current_provider_index < len(self.providers):
            pool = getattr(self.providers[self.current_provider_index], "pool", None)
            if pool:
                return sum(k.quota_failures for k in pool.keys)
        return 0

    def _sync_status(self, health: str):
        if self.obs:
            self.obs.update_provider_status(
                health=health,
                current_provider=self.model_name,
                current_key=self.current_key,
                retry_count=self.total_retries,
                fallback_count=self.total_fallbacks,
                quota_failures=self.quota_failures,
                last_error=self.last_error,
                last_failure_timestamp=self.last_failure_timestamp
            )

    def generate_with_obs(self, agent_name: str, prompt: str, system_prompt: str = "") -> str:
        start_time = time.time()
        if self.obs:
            self.obs.log_trace(f"{agent_name}Started")
            self.obs.log_execution(agent_name, "START", "RUNNING", 0)

        while self.current_provider_index < len(self.providers):
            provider = self.providers[self.current_provider_index]
            attempt = 1
            
            while attempt <= self.retry_policy.max_attempts:
                if self.obs:
                    self.obs.log_trace("ProviderRequestStarted")
                
                try:
                    response = provider.generate(prompt, system_prompt)
                    
                    if self.obs:
                        self.obs.log_trace("ProviderRequestSucceeded")
                        
                    if attempt > 1 and self.obs:
                        self.obs.log_trace("ProviderRecovered")

                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Compute health based on fallbacks and retries
                    health = "HEALTHY"
                    if self.total_fallbacks > 0 or self.total_retries > 0:
                        health = "DEGRADED"
                        
                    self._sync_status(health)
                    
                    if self.obs:
                        self.obs.log_execution(agent_name, "COMPLETE", "SUCCESS", duration_ms)
                        self.obs.record_execution(
                            agent=agent_name,
                            model=provider.model_name,
                            duration_ms=duration_ms,
                            status="SUCCESS",
                            prompt=prompt,
                            system_prompt=system_prompt,
                            response=response
                        )
                        self.obs.track_timeline(agent_name, duration_ms)
                        self.obs.log_trace(f"{agent_name}Completed")
                    return response

                except Exception as e:
                    self.last_error = str(e)
                    from karsa.observability.trace import get_iso_timestamp
                    self.last_failure_timestamp = get_iso_timestamp()
                    self._sync_status("DEGRADED")
                    
                    if self.obs:
                        self.obs.log_trace("ProviderRequestFailed")
                        # Log quota exceeded at ProviderManager level
                        error_msg = str(e).lower()
                        if "429" in error_msg or "quota" in error_msg:
                            self.obs.log_trace("QuotaExceeded")
                    
                    if not self.retry_policy.should_retry(e):
                        break
                        
                    if attempt < self.retry_policy.max_attempts:
                        self.total_retries += 1
                        self._sync_status("DEGRADED")
                        
                        backoff = self.retry_policy.get_backoff_seconds(attempt)
                        if self.obs:
                            self.obs.log_trace("RetryStarted")
                        
                        # Use a small sleep factor for testing so it doesn't hang
                        import os
                        if os.environ.get("KARSA_TESTING") == "1":
                            time.sleep(0.01)
                        else:
                            time.sleep(backoff)
                            
                        if self.obs:
                            self.obs.log_trace("RetryCompleted")
                        attempt += 1
                    else:
                        break

            # Log key rotation when falling back to next provider
            old_provider_name = provider.model_name
            old_key = getattr(provider, "current_key_fingerprint", "unknown")
            
            self.current_provider_index += 1
            if self.current_provider_index < len(self.providers):
                self.total_fallbacks += 1
                new_provider = self.providers[self.current_provider_index]
                new_key = getattr(new_provider, "current_key_fingerprint", "unknown")
                self._sync_status("DEGRADED")
                if self.obs:
                    self.obs.log_trace(f"KeyRotated:{old_key}->{new_key}")
                    self.obs.log_trace("FallbackActivated")

        duration_ms = int((time.time() - start_time) * 1000)
        self._sync_status("UNAVAILABLE")
        if self.obs:
            self.obs.log_trace("ProviderUnavailable")
            self.obs.log_execution(agent_name, "FAILED", "ERROR", duration_ms)
            self.obs.record_execution(
                agent=agent_name,
                model="ALL_FAILED",
                duration_ms=duration_ms,
                status="ERROR",
                prompt=prompt,
                system_prompt=system_prompt,
                response=f"All providers failed. Last error: {self.last_error}"
            )
            self.obs.track_timeline(agent_name, duration_ms)
            self.obs.log_trace(f"{agent_name}Completed")
        
        raise Exception(f"All providers failed. Last error: {self.last_error}")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return self.generate_with_obs("Agent", prompt, system_prompt)
