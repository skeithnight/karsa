"""LLM Router Service — multi-provider, model-group-aware routing.

Wraps the existing ProviderManager with model group abstraction.
Two groups: 'karsa-reasoning' (frontier models for thesis generation)
and 'karsa-fast' (cheap models for governance/news parsing).

Supports:
- Latency-based routing with automatic failover
- Model group selection (reasoning vs fast)
- Embedding generation via text-embedding-3-small
- Cost telemetry per group
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from karsa.llm.errors import (
    LLMProviderExhaustedError,
    QuotaExhaustedError,
    RateLimitError,
    AuthenticationError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Model group constants
GROUP_REASONING = "karsa-reasoning"
GROUP_FAST = "karsa-fast"


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM call."""
    model: str
    provider: str
    group: str
    duration_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    status: str = "success"
    error: Optional[str] = None


@dataclass
class RouterState:
    """Mutable state for the router."""
    total_calls: int = 0
    total_failures: int = 0
    total_fallbacks: int = 0
    metrics: List[LLMCallMetrics] = field(default_factory=list)
    _max_metrics: int = 1000

    def record(self, metric: LLMCallMetrics) -> None:
        self.metrics.append(metric)
        if len(self.metrics) > self._max_metrics:
            self.metrics = self.metrics[-self._max_metrics:]
        self.total_calls += 1
        if metric.status != "success":
            self.total_failures += 1


class LLMRouterService:
    """Multi-provider LLM router with model group abstraction.

    Loads configuration from the database (LLMConfigRepository) and
    routes calls to the appropriate provider based on model group,
    latency, and failover state.
    """

    def __init__(
        self,
        config_repo=None,
        credential_service=None,
        providers: Optional[Dict[str, Dict[str, Any]]] = None,
        embedding_api_key: Optional[str] = None,
        embedding_base_url: str = "https://api.openai.com/v1",
    ):
        """Initialize the router.

        Args:
            config_repo: LLMConfigRepository for DB-driven config.
            credential_service: CredentialEncryptionService for key decryption.
            providers: Static provider config (fallback if no DB config).
                Format: {"openai": {"api_key": "...", "models": {"gpt-4o": {"group": "karsa-reasoning"}}}}
            embedding_api_key: API key for embedding model.
            embedding_base_url: Base URL for embedding API.
        """
        self._config_repo = config_repo
        self._cred_service = credential_service
        self._providers = providers or {}
        self._embedding_api_key = embedding_api_key
        self._embedding_base_url = embedding_base_url
        self._state = RouterState()
        self._http_client: Optional[httpx.AsyncClient] = None

        # Model group -> list of (provider_name, model_name, priority)
        self._group_map: Dict[str, List[tuple]] = {}
        # Latency tracking for latency-based routing (EMA)
        self._latency_averages: Dict[str, float] = {}  # "provider/model" -> moving avg ms
        # Circuit breaker: consecutive failures per provider/model
        self._consecutive_failures: Dict[str, int] = {}  # "provider/model" -> count
        self._circuit_breaker_threshold = 2  # Failover after N consecutive failures
        self._build_group_map()

    def _build_group_map(self) -> None:
        """Build model group routing table from provider config."""
        for provider_name, provider_cfg in self._providers.items():
            models = provider_cfg.get("models", {})
            for model_name, model_cfg in models.items():
                group = model_cfg.get("group", GROUP_REASONING)
                priority = model_cfg.get("priority", 100)
                if group not in self._group_map:
                    self._group_map[group] = []
                self._group_map[group].append((provider_name, model_name, priority))

        # Sort each group by priority (lower = higher priority)
        for group in self._group_map:
            self._group_map[group].sort(key=lambda x: x[2])

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def call_llm(
        self,
        model_group: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Call an LLM using the specified model group.

        Tries providers in priority order with automatic failover.

        Args:
            model_group: 'karsa-reasoning' or 'karsa-fast'.
            messages: OpenAI-format message list.
            response_format: Optional response format (e.g., {"type": "json_object"}).
            temperature: Sampling temperature.
            max_tokens: Max tokens in response.

        Returns:
            Dict with 'content' (str), 'model' (str), 'usage' (dict).

        Raises:
            LLMProviderExhaustedError: All providers in group failed.
        """
        candidates = self._group_map.get(model_group, [])
        if not candidates:
            raise LLMProviderExhaustedError(f"No models configured for group '{model_group}'")

        # Filter out circuit-broken providers (>= threshold consecutive failures)
        candidates = [
            (p, m, pr) for p, m, pr in candidates
            if self._consecutive_failures.get(f"{p}/{m}", 0) < self._circuit_breaker_threshold
        ]
        if not candidates:
            # Reset all circuit breakers and retry (recovery attempt)
            self._consecutive_failures.clear()
            candidates = self._group_map.get(model_group, [])

        # Sort by latency (lowest EMA first) — latency-based routing
        candidates.sort(key=lambda x: self._latency_averages.get(f"{x[0]}/{x[1]}", 999999.0))

        last_error = None
        for provider_name, model_name, priority in candidates:
            provider_cfg = self._providers.get(provider_name, {})
            api_key = provider_cfg.get("api_key", "")
            base_url = provider_cfg.get("base_url", "https://api.openai.com/v1")

            try:
                result = await self._call_openai_compatible(
                    base_url=base_url,
                    api_key=api_key,
                    model=model_name,
                    messages=messages,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Update latency EMA and reset circuit breaker
                key = f"{provider_name}/{model_name}"
                old_avg = self._latency_averages.get(key, result.get("duration_ms", 0))
                self._latency_averages[key] = old_avg * 0.7 + result.get("duration_ms", 0) * 0.3
                self._consecutive_failures[key] = 0
                self._state.record(LLMCallMetrics(
                    model=model_name,
                    provider=provider_name,
                    group=model_group,
                    duration_ms=result.get("duration_ms", 0),
                    tokens_in=result.get("usage", {}).get("prompt_tokens", 0),
                    tokens_out=result.get("usage", {}).get("completion_tokens", 0),
                ))
                return {
                    "content": result["content"],
                    "model": model_name,
                    "provider": provider_name,
                    "usage": result.get("usage", {}),
                }
            except (RateLimitError, AuthenticationError, ProviderUnavailableError) as e:
                logger.warning(f"Provider {provider_name}/{model_name} failed: {e}")
                # Increment circuit breaker
                key = f"{provider_name}/{model_name}"
                self._consecutive_failures[key] = self._consecutive_failures.get(key, 0) + 1
                self._state.total_fallbacks += 1
                self._state.record(LLMCallMetrics(
                    model=model_name,
                    provider=provider_name,
                    group=model_group,
                    duration_ms=0,
                    status="error",
                    error=str(e),
                ))
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Unexpected error from {provider_name}/{model_name}: {e}")
                self._state.record(LLMCallMetrics(
                    model=model_name,
                    provider=provider_name,
                    group=model_group,
                    duration_ms=0,
                    status="error",
                    error=str(e),
                ))
                last_error = e
                continue

        raise LLMProviderExhaustedError(
            f"All providers in group '{model_group}' failed. Last error: {last_error}"
        )

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small",
    ) -> List[float]:
        """Generate a vector embedding for the given text.

        Args:
            text: Text to embed.
            model: Embedding model name.

        Returns:
            List of floats (1536 dimensions for text-embedding-3-small).
        """
        client = await self._get_client()
        start = time.monotonic()
        try:
            resp = await client.post(
                f"{self._embedding_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._embedding_api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": text, "model": model},
            )
            resp.raise_for_status()
            data = resp.json()
            duration_ms = int((time.monotonic() - start) * 1000)
            embedding = data["data"][0]["embedding"]
            logger.debug(f"Embedding generated: {len(embedding)}d in {duration_ms}ms")
            return embedding
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Embedding rate limited: {e}")
            raise ProviderUnavailableError(f"Embedding API error: {e}")
        except Exception as e:
            raise ProviderUnavailableError(f"Embedding failed: {e}")

    async def _call_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Call an OpenAI-compatible chat completions endpoint."""
        client = await self._get_client()
        start = time.monotonic()

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            body["response_format"] = response_format
        if max_tokens:
            body["max_tokens"] = max_tokens

        try:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            duration_ms = int((time.monotonic() - start) * 1000)

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return {
                "content": content,
                "duration_ms": duration_ms,
                "usage": usage,
            }
        except httpx.HTTPStatusError as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            if e.response.status_code == 429:
                raise RateLimitError(f"Rate limited by {model}: {e}")
            elif e.response.status_code == 401:
                raise AuthenticationError(f"Auth failed for {model}: {e}")
            elif e.response.status_code in (502, 503):
                raise ProviderUnavailableError(f"Service unavailable for {model}: {e}")
            else:
                raise ProviderUnavailableError(f"HTTP {e.response.status_code} from {model}: {e}")

    @property
    def state(self) -> RouterState:
        return self._state

    @property
    def available_groups(self) -> List[str]:
        return list(self._group_map.keys())

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
