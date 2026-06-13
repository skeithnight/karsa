import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.providers.domain.repositories import ProviderDefinitionRepository, ProviderHealthStateRepository
from karsa.providers.domain.models import (
    ProviderDefinition, ProviderHealthState, ProviderURN, ProviderPricing, 
    ProviderCapabilityMapping, ProviderLifecycleState, ProviderHealthStatus,
    ImmutableList
)

def serialize_provider_definition(definition: ProviderDefinition) -> Dict[str, Any]:
    return {
        "provider_id": definition.provider_id,
        "provider_urn": definition.provider_urn.to_string() if definition.provider_urn else None,
        "state": definition.state.value,
        "pricing": {
            "input_rate_per_1m": definition.pricing.input_rate_per_1m,
            "output_rate_per_1m": definition.pricing.output_rate_per_1m,
            "currency": definition.pricing.currency
        } if definition.pricing else None,
        "capability_mappings": [
            {
                "mapping_id": m.mapping_id,
                "capability_urn": m.capability_urn,
                "json_mode": m.json_mode,
                "tool_calling": m.tool_calling,
                "streaming": m.streaming,
                "context_window": m.context_window,
                "structured_output": m.structured_output,
                "reasoning_support": m.reasoning_support
            } for m in definition.capability_mappings
        ],
        "aggregate_version": definition.aggregate_version,
        "created_at": definition.created_at.isoformat(),
        "updated_at": definition.updated_at.isoformat()
    }

def deserialize_provider_definition(data: Dict[str, Any]) -> ProviderDefinition:
    urn = ProviderURN.from_string(data["provider_urn"]) if data.get("provider_urn") else None
    pricing = None
    if data.get("pricing"):
        pricing = ProviderPricing(
            input_rate_per_1m=data["pricing"]["input_rate_per_1m"],
            output_rate_per_1m=data["pricing"]["output_rate_per_1m"],
            currency=data["pricing"].get("currency", "USD")
        )
    mappings = []
    for m in data.get("capability_mappings", []):
        mappings.append(ProviderCapabilityMapping(
            mapping_id=m["mapping_id"],
            capability_urn=m["capability_urn"],
            json_mode=m.get("json_mode", True),
            tool_calling=m.get("tool_calling", True),
            streaming=m.get("streaming", True),
            context_window=m.get("context_window", 8192),
            structured_output=m.get("structured_output", True),
            reasoning_support=m.get("reasoning_support", False)
        ))
    
    definition = ProviderDefinition(
        provider_id=data["provider_id"],
        provider_urn=urn,
        pricing=pricing,
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"])
    )
    object.__setattr__(definition, "state", ProviderLifecycleState(data["state"]))
    object.__setattr__(definition, "capability_mappings", ImmutableList(mappings, definition, "capability_mappings"))
    object.__setattr__(definition, "aggregate_version", data.get("aggregate_version", 0))
    return definition

def serialize_provider_health_state(health: ProviderHealthState) -> Dict[str, Any]:
    return {
        "provider_id": health.provider_id,
        "health_status": health.health_status.value,
        "success_count": health.success_count,
        "failure_count": health.failure_count,
        "consecutive_failures": health.consecutive_failures,
        "average_latency_ms": health.average_latency_ms,
        "last_failure_at": health.last_failure_at.isoformat() if health.last_failure_at else None,
        "last_success_at": health.last_success_at.isoformat() if health.last_success_at else None,
        "degraded_threshold": health.degraded_threshold,
        "suspended_threshold": health.suspended_threshold,
        "aggregate_version": health.aggregate_version
    }

def deserialize_provider_health_state(data: Dict[str, Any]) -> ProviderHealthState:
    health = ProviderHealthState(
        provider_id=data["provider_id"],
        health_status=ProviderHealthStatus(data["health_status"]),
        success_count=data["success_count"],
        failure_count=data["failure_count"],
        consecutive_failures=data["consecutive_failures"],
        average_latency_ms=data["average_latency_ms"],
        last_failure_at=datetime.fromisoformat(data["last_failure_at"]) if data.get("last_failure_at") else None,
        last_success_at=datetime.fromisoformat(data["last_success_at"]) if data.get("last_success_at") else None,
        degraded_threshold=data.get("degraded_threshold", 3),
        suspended_threshold=data.get("suspended_threshold", 5)
    )
    object.__setattr__(health, "aggregate_version", data.get("aggregate_version", 0))
    return health


class InMemoryProviderDefinitionRepository(ProviderDefinitionRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, provider: ProviderDefinition) -> None:
        provider_id = provider.provider_id
        if provider_id in self._data:
            stored = self._data[provider_id]
            stored_version = stored["aggregate_version"]
            if stored_version != provider.aggregate_version and stored_version != provider.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on ProviderDefinition {provider_id}: "
                    f"stored version {stored_version}, saving version {provider.aggregate_version}"
                )
        self._data[provider_id] = serialize_provider_definition(provider)

    def find_by_id(self, provider_id: str) -> Optional[ProviderDefinition]:
        data = self._data.get(provider_id)
        if not data:
            return None
        return deserialize_provider_definition(data)

    def find_by_urn(self, urn: ProviderURN) -> Optional[ProviderDefinition]:
        urn_str = urn.to_string()
        for data in self._data.values():
            if data.get("provider_urn") == urn_str:
                return deserialize_provider_definition(data)
        return None

    def find_active_for_capability(self, capability_urn: str) -> List[ProviderDefinition]:
        active_providers = []
        for data in self._data.values():
            if data["state"] not in (
                ProviderLifecycleState.DRAFT.value, 
                ProviderLifecycleState.REVIEW.value, 
                ProviderLifecycleState.SUSPENDED.value, 
                ProviderLifecycleState.RETIRED.value
            ):
                for m in data.get("capability_mappings", []):
                    if m["capability_urn"] == capability_urn:
                        active_providers.append(deserialize_provider_definition(data))
                        break
        return active_providers


class InMemoryProviderHealthStateRepository(ProviderHealthStateRepository):
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def save(self, health: ProviderHealthState) -> None:
        provider_id = health.provider_id
        if provider_id in self._data:
            stored = self._data[provider_id]
            stored_version = stored["aggregate_version"]
            if stored_version != health.aggregate_version and stored_version != health.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict on ProviderHealthState {provider_id}: "
                    f"stored version {stored_version}, saving version {health.aggregate_version}"
                )
        self._data[provider_id] = serialize_provider_health_state(health)

    def find_by_provider_id(self, provider_id: str) -> Optional[ProviderHealthState]:
        data = self._data.get(provider_id)
        if not data:
            return None
        return deserialize_provider_health_state(data)


class FileProviderDefinitionRepository(ProviderDefinitionRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "providers" / "definitions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, provider_id: str) -> Path:
        return self.base_dir / f"{provider_id}.json"

    def save(self, provider: ProviderDefinition) -> None:
        path = self._get_path(provider.provider_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    stored = json.load(f)
                stored_version = stored.get("aggregate_version", 0)
                if stored_version != provider.aggregate_version and stored_version != provider.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict on ProviderDefinition {provider.provider_id}: "
                        f"stored version {stored_version}, saving version {provider.aggregate_version}"
                    )
            except (json.JSONDecodeError, OSError):
                # If file is corrupted, allow save to overwrite it
                pass
        serialized_data = serialize_provider_definition(provider)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, provider_id: str) -> Optional[ProviderDefinition]:
        path = self._get_path(provider_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_provider_definition(data)
        except Exception:
            return None

    def find_by_urn(self, urn: ProviderURN) -> Optional[ProviderDefinition]:
        urn_str = urn.to_string()
        if not self.base_dir.exists():
            return None
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("provider_urn") == urn_str:
                        return deserialize_provider_definition(data)
                except Exception:
                    continue
        return None

    def find_active_for_capability(self, capability_urn: str) -> List[ProviderDefinition]:
        active_providers = []
        if not self.base_dir.exists():
            return []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("state") not in (
                        ProviderLifecycleState.DRAFT.value, 
                        ProviderLifecycleState.REVIEW.value, 
                        ProviderLifecycleState.SUSPENDED.value, 
                        ProviderLifecycleState.RETIRED.value
                    ):
                        for m in data.get("capability_mappings", []):
                            if m["capability_urn"] == capability_urn:
                                active_providers.append(deserialize_provider_definition(data))
                                break
                except Exception:
                    continue
        return active_providers


class FileProviderHealthStateRepository(ProviderHealthStateRepository):
    def __init__(self, workspace_path: Optional[Path] = None):
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "providers" / "health"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, provider_id: str) -> Path:
        return self.base_dir / f"{provider_id}.json"

    def save(self, health: ProviderHealthState) -> None:
        path = self._get_path(health.provider_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    stored = json.load(f)
                stored_version = stored.get("aggregate_version", 0)
                if stored_version != health.aggregate_version and stored_version != health.aggregate_version - 1:
                    raise ConcurrencyConflictError(
                        f"Concurrency conflict on ProviderHealthState {health.provider_id}: "
                        f"stored version {stored_version}, saving version {health.aggregate_version}"
                    )
            except (json.JSONDecodeError, OSError):
                pass
        serialized_data = serialize_provider_health_state(health)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_provider_id(self, provider_id: str) -> Optional[ProviderHealthState]:
        path = self._get_path(provider_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_provider_health_state(data)
        except Exception:
            return None
