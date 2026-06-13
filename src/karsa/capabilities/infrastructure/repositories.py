import json
import os
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
from karsa.capabilities.domain.models import (
    CapabilityDefinition, CapabilityExecution, CapabilityURN,
    CapabilityOwner, CapabilityLifecycleState, ExecutionContract,
    ExecutionStatus, ExecutionBudget, ExecutionTelemetry,
    ExecutionSchema, CapabilityDependency, ContractFingerprint
)
from karsa.capabilities.domain.repositories import (
    CapabilityDefinitionRepository, CapabilityExecutionRepository
)

class InMemoryCapabilityDefinitionRepository(CapabilityDefinitionRepository):
    def __init__(self):
        self._by_id: Dict[str, CapabilityDefinition] = {}
        self._by_urn: Dict[str, CapabilityDefinition] = {}

    def save(self, definition: CapabilityDefinition) -> None:
        self._by_id[definition.capability_id] = definition
        if definition.urn:
            self._by_urn[definition.urn.to_string()] = definition

    def find_by_id(self, capability_id: str) -> Optional[CapabilityDefinition]:
        return self._by_id.get(capability_id)

    def find_by_urn(self, urn: CapabilityURN) -> Optional[CapabilityDefinition]:
        return self._by_urn.get(urn.to_string())

    def find_by_family(self, capability_family_id: str) -> List[CapabilityDefinition]:
        return [d for d in self._by_id.values() if d.capability_family_id == capability_family_id]

    def find_active(self) -> List[CapabilityDefinition]:
        return [d for d in self._by_id.values() if d.state == CapabilityLifecycleState.ACTIVE]

class InMemoryCapabilityExecutionRepository(CapabilityExecutionRepository):
    def __init__(self):
        self._by_id: Dict[str, CapabilityExecution] = {}

    def save(self, execution: CapabilityExecution) -> None:
        self._by_id[execution.execution_id] = execution

    def find_by_id(self, execution_id: str) -> Optional[CapabilityExecution]:
        return self._by_id.get(execution_id)

class FileCapabilityDefinitionRepository(CapabilityDefinitionRepository):
    def __init__(self, workspace_path: Path):
        self.base_dir = workspace_path / ".karsa" / "capabilities" / "definitions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, capability_id: str) -> Path:
        return self.base_dir / f"{capability_id}.json"

    def _serialize(self, definition: CapabilityDefinition) -> Dict[str, Any]:
        schema_data = None
        if definition.schema_contract:
            schema_data = {
                "input_schema": definition.schema_contract.input_schema,
                "output_schema": definition.schema_contract.output_schema,
                "preconditions": definition.schema_contract.preconditions,
                "postconditions": definition.schema_contract.postconditions,
                "required_json_mode": definition.schema_contract.required_json_mode,
                "required_tool_calling": definition.schema_contract.required_tool_calling,
                "required_streaming": definition.schema_contract.required_streaming,
                "required_context_window": definition.schema_contract.required_context_window,
                "required_structured_output": definition.schema_contract.required_structured_output,
                "required_reasoning_support": definition.schema_contract.required_reasoning_support
            }
        
        fingerprint_hash = None
        if definition.contract_fingerprint:
            fingerprint_hash = definition.contract_fingerprint.sha256_hash

        deps = []
        for d in definition.dependencies:
            deps.append({
                "dependency_id": d.dependency_id,
                "dependency_urn": d.dependency_urn
            })

        return {
            "capability_id": definition.capability_id,
            "capability_family_id": definition.capability_family_id,
            "urn_str": definition.urn.to_string() if definition.urn else "",
            "owner": {
                "owner_id": definition.owner.owner_id if definition.owner else "",
                "owner_type": definition.owner.owner_type if definition.owner else ""
            },
            "state": definition.state.value,
            "schema_contract": schema_data,
            "contract_fingerprint": fingerprint_hash,
            "dependencies": deps,
            "aggregate_version": definition.aggregate_version,
            "created_at": definition.created_at.isoformat(),
            "updated_at": definition.updated_at.isoformat()
        }

    def _deserialize(self, data: Dict[str, Any]) -> CapabilityDefinition:
        urn = CapabilityURN.from_string(data["urn_str"]) if data.get("urn_str") else None
        owner = None
        if data.get("owner"):
            owner = CapabilityOwner(
                owner_id=data["owner"].get("owner_id", ""),
                owner_type=data["owner"].get("owner_type", "")
            )
        
        schema_contract = None
        if data.get("schema_contract"):
            sc = data["schema_contract"]
            schema_contract = ExecutionSchema(
                input_schema=sc["input_schema"],
                output_schema=sc["output_schema"],
                preconditions=sc.get("preconditions", []),
                postconditions=sc.get("postconditions", []),
                required_json_mode=sc.get("required_json_mode", False),
                required_tool_calling=sc.get("required_tool_calling", False),
                required_streaming=sc.get("required_streaming", False),
                required_context_window=sc.get("required_context_window", 8192),
                required_structured_output=sc.get("required_structured_output", True),
                required_reasoning_support=sc.get("required_reasoning_support", False)
            )

        fingerprint = None
        if data.get("contract_fingerprint"):
            fingerprint = ContractFingerprint(sha256_hash=data["contract_fingerprint"])

        dependencies = []
        if data.get("dependencies"):
            for d in data["dependencies"]:
                dependencies.append(CapabilityDependency(
                    dependency_id=d["dependency_id"],
                    dependency_urn=d["dependency_urn"]
                ))

        definition = CapabilityDefinition(
            capability_id=data["capability_id"],
            capability_family_id=data.get("capability_family_id", ""),
            urn=urn,
            owner=owner,
            state=CapabilityLifecycleState(data["state"]),
            schema_contract=schema_contract,
            contract_fingerprint=fingerprint,
            dependencies=dependencies,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
        definition.aggregate_version = data.get("aggregate_version", 0)
        return definition

    def save(self, definition: CapabilityDefinition) -> None:
        path = self._get_path(definition.capability_id)
        serialized_data = self._serialize(definition)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, capability_id: str) -> Optional[CapabilityDefinition]:
        path = self._get_path(capability_id)
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return self._deserialize(data)

    def find_by_urn(self, urn: CapabilityURN) -> Optional[CapabilityDefinition]:
        urn_str = urn.to_string()
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("urn_str") == urn_str:
                        return self._deserialize(data)
                except Exception:
                    continue
        return None

    def find_by_family(self, capability_family_id: str) -> List[CapabilityDefinition]:
        results = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("capability_family_id") == capability_family_id:
                        results.append(self._deserialize(data))
                except Exception:
                    continue
        return results

    def find_active(self) -> List[CapabilityDefinition]:
        results = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("state") == CapabilityLifecycleState.ACTIVE.value:
                        results.append(self._deserialize(data))
                except Exception:
                    continue
        return results

class FileCapabilityExecutionRepository(CapabilityExecutionRepository):
    def __init__(self, workspace_path: Path):
        self.base_dir = workspace_path / ".karsa" / "capabilities" / "executions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, execution_id: str) -> Path:
        return self.base_dir / f"{execution_id}.json"

    def _serialize(self, execution: CapabilityExecution) -> Dict[str, Any]:
        telemetry_data = None
        if execution.telemetry:
            telemetry_data = {
                "duration_ms": execution.telemetry.duration_ms,
                "input_tokens": execution.telemetry.input_tokens,
                "output_tokens": execution.telemetry.output_tokens,
                "cost_usd": execution.telemetry.cost_usd,
                "system_metrics": execution.telemetry.system_metrics
            }

        return {
            "execution_id": execution.execution_id,
            "capability_urn_str": execution.capability_urn.to_string() if execution.capability_urn else "",
            "correlation_id": execution.correlation_id,
            "causation_id": execution.causation_id,
            "workspace_id": execution.workspace_id,
            "branch_id": execution.branch_id,
            "status": execution.status.value,
            "budget": {
                "max_cost_usd": execution.budget.max_cost_usd,
                "max_input_tokens": execution.budget.max_input_tokens,
                "max_output_tokens": execution.budget.max_output_tokens,
                "timeout_ms": execution.budget.timeout_ms
            },
            "input_payload": execution.input_payload,
            "output_payload": execution.output_payload,
            "error_message": execution.error_message,
            "telemetry": telemetry_data,
            "aggregate_version": execution.aggregate_version,
            "created_at": execution.created_at.isoformat()
        }

    def _deserialize(self, data: Dict[str, Any]) -> CapabilityExecution:
        urn = CapabilityURN.from_string(data["capability_urn_str"]) if data.get("capability_urn_str") else None
        budget = ExecutionBudget(
            max_cost_usd=data["budget"]["max_cost_usd"],
            max_input_tokens=data["budget"]["max_input_tokens"],
            max_output_tokens=data["budget"]["max_output_tokens"],
            timeout_ms=data["budget"]["timeout_ms"]
        )
        telemetry = None
        if data.get("telemetry"):
            telemetry = ExecutionTelemetry(
                duration_ms=data["telemetry"]["duration_ms"],
                input_tokens=data["telemetry"]["input_tokens"],
                output_tokens=data["telemetry"]["output_tokens"],
                cost_usd=data["telemetry"]["cost_usd"],
                system_metrics=data["telemetry"].get("system_metrics", {})
            )

        execution = CapabilityExecution(
            execution_id=data["execution_id"],
            capability_urn=urn,
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            workspace_id=data["workspace_id"],
            branch_id=data["branch_id"],
            status=ExecutionStatus(data["status"]),
            budget=budget,
            input_payload=data["input_payload"],
            output_payload=data.get("output_payload"),
            error_message=data.get("error_message"),
            telemetry=telemetry,
            created_at=datetime.fromisoformat(data["created_at"])
        )
        execution.aggregate_version = data.get("aggregate_version", 0)
        return execution

    def save(self, execution: CapabilityExecution) -> None:
        path = self._get_path(execution.execution_id)
        serialized_data = self._serialize(execution)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, execution_id: str) -> Optional[CapabilityExecution]:
        path = self._get_path(execution_id)
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return self._deserialize(data)
