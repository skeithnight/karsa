import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional, List
from karsa.capabilities.domain.models import (
    CapabilityDefinition, CapabilityExecution, CapabilityURN,
    CapabilityOwner, CapabilityLifecycleState, ExecutionContract,
    ExecutionStatus, ExecutionBudget, ExecutionTelemetry,
    ExecutionSchema, CapabilityDependency, ContractFingerprint
)
from karsa.capabilities.domain.repositories import (
    CapabilityDefinitionRepository, CapabilityExecutionRepository
)
from karsa.capabilities.domain.events import (
    CapabilityRegisteredEvent, CapabilityActivatedEvent,
    CapabilityDeprecatedEvent, CapabilitySuspendedEvent,
    CapabilityRevokedEvent, DependencyValidatedEvent,
    CapabilityLifecycleTransitionedEvent,
    CapabilityExecutionStartedEvent, CapabilityExecutionCompletedEvent,
    CapabilityExecutionFailedEvent
)
from karsa.capabilities.application.adapters import ProviderAdapter

class DependencyCycleException(Exception):
    pass

class DependencyValidationService:
    def __init__(self, definition_repo: CapabilityDefinitionRepository):
        self.definition_repo = definition_repo

    def validate_dependencies(self, definition: CapabilityDefinition) -> None:
        visited = {}  # capability_id -> color (0=White, 1=Gray, 2=Black)
        
        def dfs(node_id: str):
            visited[node_id] = 1  # Gray: visiting
            node = self.definition_repo.find_by_id(node_id)
            if not node:
                visited[node_id] = 2  # Black: visited (missing node is not a cycle)
                return

            for dep in node.dependencies:
                dep_id = dep.dependency_id
                color = visited.get(dep_id, 0)
                if color == 1:
                    raise DependencyCycleException(f"Circular dependency detected containing capability ID: {dep_id}")
                elif color == 0:
                    dfs(dep_id)
            visited[node_id] = 2  # Black: visited

        visited[definition.capability_id] = 1
        for dep in definition.dependencies:
            dep_id = dep.dependency_id
            color = visited.get(dep_id, 0)
            if color == 1:
                raise DependencyCycleException(f"Circular dependency detected containing capability ID: {dep_id}")
            elif color == 0:
                dfs(dep_id)
        visited[definition.capability_id] = 2

class ContractFingerprintService:
    @staticmethod
    def verify_compatibility(old_fingerprint: ContractFingerprint, new_fingerprint: ContractFingerprint) -> bool:
        return old_fingerprint.sha256_hash == new_fingerprint.sha256_hash

class DependencyGraphProjection:
    def __init__(self, definition_repo: CapabilityDefinitionRepository):
        self.definition_repo = definition_repo

    def get_dependency_dag(self, root_capability_id: str) -> Dict[str, List[str]]:
        adj_list = {}
        visited = set()

        def traverse(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            node = self.definition_repo.find_by_id(node_id)
            if not node:
                adj_list[node_id] = []
                return
            
            deps = [d.dependency_id for d in node.dependencies]
            adj_list[node_id] = deps
            for dep_id in deps:
                traverse(dep_id)

        traverse(root_capability_id)
        return adj_list

class RegistryQueryService:
    def __init__(self, definition_repo: CapabilityDefinitionRepository):
        self.definition_repo = definition_repo

    def get_active_capabilities(self) -> List[CapabilityDefinition]:
        return self.definition_repo.find_active()

    def get_capability_family_versions(self, family_id: str) -> List[CapabilityDefinition]:
        return self.definition_repo.find_by_family(family_id)

    def resolve_urn(self, urn_str: str) -> Optional[CapabilityDefinition]:
        try:
            urn = CapabilityURN.from_string(urn_str)
            return self.definition_repo.find_by_urn(urn)
        except Exception:
            return None

class CapabilityRegistryService:
    def __init__(
        self,
        definition_repo: CapabilityDefinitionRepository,
        event_publisher: Optional[Callable[[Any], None]] = None,
        governance_callback: Optional[Callable[[str, str], bool]] = None
    ):
        self.definition_repo = definition_repo
        self.event_publisher = event_publisher
        self.governance_callback = governance_callback
        self.validator = DependencyValidationService(definition_repo)

    def register_capability(
        self,
        capability_id: str,
        capability_family_id: str,
        urn_str: str,
        owner_id: str,
        owner_type: str,
        schema_contract: ExecutionSchema,
        dependencies: List[CapabilityDependency] = None
    ) -> CapabilityDefinition:
        urn = CapabilityURN.from_string(urn_str)
        
        if self.definition_repo.find_by_id(capability_id):
            raise ValueError(f"Capability with ID {capability_id} already exists.")
        if self.definition_repo.find_by_urn(urn):
            raise ValueError(f"Capability URN {urn_str} already exists.")

        new_fingerprint = ContractFingerprint.generate(
            schema_contract.input_schema,
            schema_contract.output_schema
        )

        owner = CapabilityOwner(owner_id=owner_id, owner_type=owner_type)
        
        definition = CapabilityDefinition(
            capability_id=capability_id,
            capability_family_id=capability_family_id,
            urn=urn,
            owner=owner,
            state=CapabilityLifecycleState.DRAFT,
            schema_contract=schema_contract,
            contract_fingerprint=new_fingerprint,
            dependencies=dependencies or []
        )

        self.definition_repo.save(definition)

        event = CapabilityRegisteredEvent(
            capability_id=capability_id,
            capability_family_id=capability_family_id,
            urn_str=urn_str,
            owner_id=owner_id,
            owner_type=owner_type,
            input_schema=schema_contract.input_schema,
            output_schema=schema_contract.output_schema,
            contract_fingerprint=new_fingerprint.sha256_hash
        )
        if self.event_publisher:
            self.event_publisher(event)

        return definition

    def promote_to_review(self, capability_id: str) -> None:
        definition = self.definition_repo.find_by_id(capability_id)
        if not definition:
            raise ValueError(f"Capability definition not found: {capability_id}")
            
        definition.transition_to(CapabilityLifecycleState.REVIEW)
        self.definition_repo.save(definition)

    def activate_capability(self, capability_id: str, reason: str = "") -> None:
        definition = self.definition_repo.find_by_id(capability_id)
        if not definition:
            raise ValueError(f"Capability definition not found: {capability_id}")

        self.validator.validate_dependencies(definition)

        dep_event = DependencyValidatedEvent(
            capability_id=capability_id,
            capability_family_id=definition.capability_family_id,
            urn_str=definition.urn.to_string() if definition.urn else "",
            validated_dependencies=[d.dependency_id for d in definition.dependencies]
        )
        if self.event_publisher:
            self.event_publisher(dep_event)

        if self.governance_callback:
            approved = self.governance_callback(capability_id, "ACTIVE")
            if not approved:
                definition.transition_to(CapabilityLifecycleState.RETIRED, "Governance rejection")
                self.definition_repo.save(definition)
                return

        definition.transition_to(CapabilityLifecycleState.ACTIVE, reason)
        self.definition_repo.save(definition)

        event = CapabilityActivatedEvent(
            capability_id=capability_id,
            capability_family_id=definition.capability_family_id,
            urn_str=definition.urn.to_string() if definition.urn else "",
            reason=reason
        )
        if self.event_publisher:
            self.event_publisher(event)

    def deprecate_capability(self, capability_id: str, reason: str = "") -> None:
        definition = self.definition_repo.find_by_id(capability_id)
        if not definition:
            raise ValueError(f"Capability definition not found: {capability_id}")
        
        definition.transition_to(CapabilityLifecycleState.DEPRECATED, reason)
        self.definition_repo.save(definition)

        event = CapabilityDeprecatedEvent(
            capability_id=capability_id,
            capability_family_id=definition.capability_family_id,
            urn_str=definition.urn.to_string() if definition.urn else "",
            reason=reason
        )
        if self.event_publisher:
            self.event_publisher(event)

    def suspend_capability(self, capability_id: str, reason: str = "") -> None:
        definition = self.definition_repo.find_by_id(capability_id)
        if not definition:
            raise ValueError(f"Capability definition not found: {capability_id}")
        
        definition.transition_to(CapabilityLifecycleState.SUSPENDED, reason)
        self.definition_repo.save(definition)

        event = CapabilitySuspendedEvent(
            capability_id=capability_id,
            capability_family_id=definition.capability_family_id,
            urn_str=definition.urn.to_string() if definition.urn else "",
            reason=reason
        )
        if self.event_publisher:
            self.event_publisher(event)

    def revoke_capability(self, capability_id: str, reason: str = "") -> None:
        definition = self.definition_repo.find_by_id(capability_id)
        if not definition:
            raise ValueError(f"Capability definition not found: {capability_id}")
        
        definition.transition_to(CapabilityLifecycleState.REVOKED, reason)
        self.definition_repo.save(definition)

        event = CapabilityRevokedEvent(
            capability_id=capability_id,
            capability_family_id=definition.capability_family_id,
            urn_str=definition.urn.to_string() if definition.urn else "",
            reason=reason
        )
        if self.event_publisher:
            self.event_publisher(event)

    def retire_capability(self, capability_id: str, reason: str = "") -> None:
        definition = self.definition_repo.find_by_id(capability_id)
        if not definition:
            raise ValueError(f"Capability definition not found: {capability_id}")
        
        definition.transition_to(CapabilityLifecycleState.RETIRED, reason)
        self.definition_repo.save(definition)

class CapabilityRegistrationService:
    def __init__(
        self,
        definition_repo: CapabilityDefinitionRepository,
        event_publisher: Optional[Callable[[Any], None]] = None
    ):
        self.registry = CapabilityRegistryService(
            definition_repo=definition_repo,
            event_publisher=event_publisher
        )

    def register_capability(
        self,
        capability_id: str,
        urn_str: str,
        owner_id: str,
        owner_type: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None
    ) -> CapabilityDefinition:
        schema = ExecutionSchema(
            input_schema=input_schema,
            output_schema=output_schema,
            preconditions=preconditions or [],
            postconditions=postconditions or []
        )
        return self.registry.register_capability(
            capability_id=capability_id,
            capability_family_id=capability_id,
            urn_str=urn_str,
            owner_id=owner_id,
            owner_type=owner_type,
            schema_contract=schema
        )

    def verify_and_activate(self, capability_id: str, approval_decision_type: str, reason: str = "") -> None:
        if approval_decision_type == "ALLOW":
            self.registry.promote_to_review(capability_id)
            self.registry.activate_capability(capability_id, reason)
        else:
            self.registry.promote_to_review(capability_id)
            self.registry.retire_capability(capability_id, reason)

class ExecutionReplayService:
    def __init__(self, evidence_registry: Dict[str, Dict[str, Any]]):
        self.evidence_registry = evidence_registry

    def _canonical_hash(self, payload: Dict[str, Any]) -> str:
        canonical_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def fetch_replay_outcome(self, execution_id: str, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        evidence = self.evidence_registry.get(execution_id)
        if not evidence:
            raise ValueError(f"No historical evidence found for execution ID: {execution_id}")

        historical_input = evidence["input_payload"]
        historical_hash = self._canonical_hash(historical_input)
        current_hash = self._canonical_hash(input_payload)

        if historical_hash != current_hash:
            raise ValueError(
                f"Replay divergence detected: Input parameters changed for execution ID {execution_id}. "
                f"Expected hash: {historical_hash}, Got: {current_hash}"
            )

        return evidence["output_payload"]

class CapabilityExecutionService:
    def __init__(
        self,
        definition_repo: CapabilityDefinitionRepository,
        execution_repo: CapabilityExecutionRepository,
        provider_adapter: ProviderAdapter,
        replay_service: ExecutionReplayService,
        governance_pep_callback: Optional[Callable[[str, Dict[str, Any], ExecutionBudget], Any]] = None,
        event_publisher: Optional[Callable[[Any], None]] = None,
        replay_mode: bool = False
    ):
        self.definition_repo = definition_repo
        self.execution_repo = execution_repo
        self.provider_adapter = provider_adapter
        self.replay_service = replay_service
        self.governance_pep_callback = governance_pep_callback
        self.event_publisher = event_publisher
        self.replay_mode = replay_mode

    def execute(
        self,
        execution_id: str,
        capability_urn_str: str,
        correlation_id: str,
        causation_id: str,
        workspace_id: str,
        branch_id: str,
        input_payload: Dict[str, Any],
        budget: ExecutionBudget
    ) -> Dict[str, Any]:
        urn = CapabilityURN.from_string(capability_urn_str)
        
        definition = self.definition_repo.find_by_urn(urn)
        
        if self.replay_mode:
            if definition and definition.state == CapabilityLifecycleState.REVOKED:
                raise PermissionError(f"Replay blocked: Capability {capability_urn_str} has been permanently REVOKED.")
            return self.replay_service.fetch_replay_outcome(execution_id, input_payload)

        if not definition:
            raise ValueError(f"Capability URN not registered: {capability_urn_str}")

        if definition.state not in (CapabilityLifecycleState.ACTIVE, CapabilityLifecycleState.DEPRECATED):
            raise ValueError(f"Capability {capability_urn_str} is in state {definition.state.value} and cannot be executed.")

        definition.validate_input(input_payload)

        if self.governance_pep_callback:
            decision = self.governance_pep_callback(capability_urn_str, input_payload, budget)
            if decision.decision_type == "DENY":
                raise PermissionError(f"Governance enforcement blocked execution: {decision.reason}")

        execution = CapabilityExecution(
            execution_id=execution_id,
            capability_urn=urn,
            correlation_id=correlation_id,
            causation_id=causation_id,
            workspace_id=workspace_id,
            branch_id=branch_id,
            status=ExecutionStatus.QUEUED,
            budget=budget,
            input_payload=input_payload
        )
        self.execution_repo.save(execution)

        started_event = CapabilityExecutionStartedEvent(
            execution_id=execution_id,
            capability_urn_str=capability_urn_str,
            correlation_id=correlation_id,
            causation_id=causation_id,
            workspace_id=workspace_id,
            branch_id=branch_id,
            input_payload=input_payload
        )
        if self.event_publisher:
            self.event_publisher(started_event)

        execution.start()
        self.execution_repo.save(execution)

        start_time = time.perf_counter()
        try:
            output = self.provider_adapter.execute_capability(urn, input_payload, budget)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            definition.validate_output(output)

            telemetry = ExecutionTelemetry(
                duration_ms=duration_ms,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                system_metrics={"oom_killed": False}
            )

            execution.complete(output, telemetry)
            self.execution_repo.save(execution)

            completed_event = CapabilityExecutionCompletedEvent(
                execution_id=execution_id,
                output_payload=output,
                telemetry={
                    "duration_ms": duration_ms,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0
                }
            )
            if self.event_publisher:
                self.event_publisher(completed_event)

            return output

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            telemetry = ExecutionTelemetry(
                duration_ms=duration_ms,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                system_metrics={"oom_killed": False}
            )
            execution.fail(str(e), telemetry)
            self.execution_repo.save(execution)

            failed_event = CapabilityExecutionFailedEvent(
                execution_id=execution_id,
                failure_reason=type(e).__name__,
                error_message=str(e)
            )
            if self.event_publisher:
                self.event_publisher(failed_event)
            
            raise e
