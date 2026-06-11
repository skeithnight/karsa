import time
import hashlib
import json
from pathlib import Path
from typing import List, Optional, Callable

class ProviderKey:
    def __init__(self, key: str):
        self.key = key
        self.fingerprint = hashlib.sha256(key.encode()).hexdigest()[:8]
        self.status = "ACTIVE"
        self.last_success = None
        self.last_failure = None
        self.quota_failures = 0
        self.total_requests = 0
        self.retry_after = 0

class ProviderPool:
    def __init__(self, provider_name: str, keys: List[str], registry_file: Path, trace_fn: Callable[[str], None] = None):
        self.provider_name = provider_name
        self.registry_file = registry_file
        self.keys = [ProviderKey(k) for k in keys]
        self.current_index = 0
        self.trace_fn = trace_fn
        self._load_registry()

    def _trace(self, event: str):
        if self.trace_fn:
            self.trace_fn(event)

    def _load_registry(self):
        if not self.registry_file.exists():
            return
        try:
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                if self.provider_name in data:
                    provider_data = data[self.provider_name]
                    for key_obj in self.keys:
                        if key_obj.fingerprint in provider_data:
                            kd = provider_data[key_obj.fingerprint]
                            key_obj.status = kd.get("status", "ACTIVE")
                            key_obj.last_success = kd.get("last_success")
                            key_obj.last_failure = kd.get("last_failure")
                            key_obj.quota_failures = kd.get("quota_failures", 0)
                            key_obj.total_requests = kd.get("total_requests", 0)
                            key_obj.retry_after = kd.get("retry_after", 0)
        except Exception:
            pass
            
    def _save_registry(self):
        data = {}
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
                
        if self.provider_name not in data:
            data[self.provider_name] = {}
            
        for key_obj in self.keys:
            data[self.provider_name][key_obj.fingerprint] = {
                "provider_name": self.provider_name,
                "key_fingerprint": key_obj.fingerprint,
                "status": key_obj.status,
                "last_success": key_obj.last_success,
                "last_failure": key_obj.last_failure,
                "quota_failures": key_obj.quota_failures,
                "total_requests": key_obj.total_requests,
                "retry_after": key_obj.retry_after
            }
            
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_next_key(self) -> Optional[ProviderKey]:
        # Recover keys if past retry_after
        now = time.time()
        for key in self.keys:
            if key.status == "SUSPENDED" and now >= key.retry_after:
                key.status = "ACTIVE"
                key.quota_failures = 0
                self._trace(f"KeyRecovered:{key.fingerprint}")
                
        # Round robin over active keys
        start_idx = self.current_index
        for _ in range(len(self.keys)):
            k = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)
            if k.status == "ACTIVE":
                self._trace(f"KeySelected:{k.fingerprint}")
                return k
                
        return None

    def mark_success(self, key: ProviderKey):
        key.status = "ACTIVE"
        key.last_success = time.time()
        key.total_requests += 1
        key.quota_failures = 0
        self._save_registry()

    def mark_failure(self, key: ProviderKey, is_quota: bool):
        key.last_failure = time.time()
        key.total_requests += 1
        if is_quota:
            key.quota_failures += 1
            key.status = "SUSPENDED"
            self._trace(f"QuotaExceeded:{key.fingerprint}")
            self._trace(f"KeySuspended:{key.fingerprint}")
            # small retry_after for tests, otherwise larger
            import os
            delay = 0.1 if os.environ.get("KARSA_TESTING") == "1" else 60
            key.retry_after = time.time() + delay
        self._save_registry()
