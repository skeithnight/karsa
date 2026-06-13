import pytest
from pathlib import Path
from karsa.capabilities.domain.models import (
    CapabilityURN, ExecutionBudget, CapabilityLifecycleState, ExecutionStatus,
    ExecutionSchema, CapabilityDependency, CapabilityDefinition, CapabilityOwner,
    ContractFingerprint
)
from karsa.capabilities.domain.events import (
    CapabilityRegisteredEvent, DependencyValidatedEvent, CapabilityActivatedEvent,
    CapabilityExecutionStartedEvent, CapabilityExecutionCompletedEvent
)
from karsa.capabilities.infrastructure.repositories import (
    InMemoryCapabilityDefinitionRepository, InMemoryCapabilityExecutionRepository,
    FileCapabilityDefinitionRepository, FileCapabilityExecutionRepository
)
from karsa.capabilities.application.adapters import MockProviderAdapter
from karsa.capabilities.application.services import (
    CapabilityRegistrationService, ExecutionReplayService, CapabilityExecutionService,
    CapabilityRegistryService, DependencyValidationService, DependencyCycleException,
    DependencyGraphProjection, RegistryQueryService
)
from karsa.domain.models import GovernanceDecision

def test_registry_services():
    def_repo = InMemoryCapabilityDefinitionRepository()
    events = []
    
    registry = CapabilityRegistryService(
        definition_repo=def_repo,
        event_publisher=events.append
    )

    schema = ExecutionSchema(
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    
    # 1. Register
    definition = registry.register_capability(
        capability_id="cap_test",
        capability_family_id="fam_test",
        urn_str="urn:karsa:capability:core:test-cap:1.0.0",
        owner_id="sys",
        owner_type="SYSTEM",
        schema_contract=schema
    )
    
    assert definition.state == CapabilityLifecycleState.DRAFT
    assert len(events) == 1
    assert isinstance(events[0], CapabilityRegisteredEvent)
    assert events[0].capability_family_id == "fam_test"

    # Promote to review
    registry.promote_to_review("cap_test")
    assert definition.state == CapabilityLifecycleState.REVIEW

    # 2. Activate
    registry.activate_capability("cap_test", "Approved by security")
    assert definition.state == CapabilityLifecycleState.ACTIVE
    assert len(events) == 3
    assert isinstance(events[1], DependencyValidatedEvent)
    assert isinstance(events[2], CapabilityActivatedEvent)

def test_dependency_cycle_detection():
    def_repo = InMemoryCapabilityDefinitionRepository()
    registry = CapabilityRegistryService(definition_repo=def_repo)
    
    schema = ExecutionSchema(input_schema={}, output_schema={})
    
    # Register 3 capabilities forming a cycle: A -> B -> C -> A
    a = registry.register_capability("A", "fam_A", "urn:karsa:capability:core:a:1.0.0", "sys", "SYSTEM", schema)
    b = registry.register_capability("B", "fam_B", "urn:karsa:capability:core:b:1.0.0", "sys", "SYSTEM", schema)
    c = registry.register_capability("C", "fam_C", "urn:karsa:capability:core:c:1.0.0", "sys", "SYSTEM", schema)
    
    # Pin dependencies exactly
    a.dependencies = [CapabilityDependency(dependency_id="B", dependency_urn="urn:karsa:capability:core:b:1.0.0")]
    b.dependencies = [CapabilityDependency(dependency_id="C", dependency_urn="urn:karsa:capability:core:c:1.0.0")]
    c.dependencies = [CapabilityDependency(dependency_id="A", dependency_urn="urn:karsa:capability:core:a:1.0.0")]
    
    def_repo.save(a)
    def_repo.save(b)
    def_repo.save(c)

    # Activating A should fail due to cycle detection
    with pytest.raises(DependencyCycleException) as excinfo:
        registry.activate_capability("A")
    assert "Circular dependency detected" in str(excinfo.value)

def test_dependency_graph_projection_and_query():
    def_repo = InMemoryCapabilityDefinitionRepository()
    registry = CapabilityRegistryService(definition_repo=def_repo)
    
    schema = ExecutionSchema(input_schema={}, output_schema={})
    
    a = registry.register_capability("A", "fam_A", "urn:karsa:capability:core:a:1.0.0", "sys", "SYSTEM", schema)
    b = registry.register_capability("B", "fam_B", "urn:karsa:capability:core:b:1.0.0", "sys", "SYSTEM", schema)
    
    a.dependencies = [CapabilityDependency(dependency_id="B", dependency_urn="urn:karsa:capability:core:b:1.0.0")]
    def_repo.save(a)
    def_repo.save(b)
    
    # Verify graph projection compiles DAG correctly
    projection = DependencyGraphProjection(def_repo)
    dag = projection.get_dependency_dag("A")
    assert dag["A"] == ["B"]
    assert dag["B"] == []

    # Query service checks
    query_service = RegistryQueryService(def_repo)
    registry.promote_to_review("B")
    registry.activate_capability("B")
    
    active = query_service.get_active_capabilities()
    assert len(active) == 1
    assert active[0].capability_id == "B"

    resolved = query_service.resolve_urn("urn:karsa:capability:core:b:1.0.0")
    assert resolved is not None
    assert resolved.capability_id == "B"

def test_governance_hook():
    def_repo = InMemoryCapabilityDefinitionRepository()
    
    # Setup registry with denying governance callback
    def deny_hook(cap_id, target_state):
        return False

    registry = CapabilityRegistryService(
        definition_repo=def_repo,
        governance_callback=deny_hook
    )
    
    schema = ExecutionSchema(input_schema={}, output_schema={})
    registry.register_capability("A", "fam_A", "urn:karsa:capability:core:a:1.0.0", "sys", "SYSTEM", schema)
    registry.promote_to_review("A")
    
    # Activation transitions node to RETIRED due to rejection
    registry.activate_capability("A")
    definition = def_repo.find_by_id("A")
    assert definition.state == CapabilityLifecycleState.RETIRED

def test_execution_replay_and_revocation():
    def_repo = InMemoryCapabilityDefinitionRepository()
    exec_repo = InMemoryCapabilityExecutionRepository()
    adapter = MockProviderAdapter()
    
    # Ingest a revoked capability definition
    schema = ExecutionSchema(input_schema={}, output_schema={})
    registry = CapabilityRegistryService(definition_repo=def_repo)
    registry.register_capability("cap_rev", "fam_rev", "urn:karsa:capability:core:bad:1.0.0", "sys", "SYSTEM", schema)
    registry.promote_to_review("cap_rev")
    registry.activate_capability("cap_rev")
    registry.revoke_capability("cap_rev")
    
    replay_service = ExecutionReplayService({
        "exec_1": {
            "input_payload": {},
            "output_payload": {"stdout": "secret"},
            "telemetry": {}
        }
    })
    
    execution_service = CapabilityExecutionService(
        definition_repo=def_repo,
        execution_repo=exec_repo,
        provider_adapter=adapter,
        replay_service=replay_service,
        replay_mode=True
    )
    
    # Replay on revoked capability must fail immediately
    with pytest.raises(PermissionError) as excinfo:
        execution_service.execute(
            execution_id="exec_1",
            capability_urn_str="urn:karsa:capability:core:bad:1.0.0",
            correlation_id="c_1",
            causation_id="ca_1",
            workspace_id="w_1",
            branch_id="b_1",
            input_payload={},
            budget=ExecutionBudget()
        )
    assert "Replay blocked: Capability urn:karsa:capability:core:bad:1.0.0 has been permanently REVOKED." in str(excinfo.value)

def test_file_based_persistence(tmp_path: Path):
    def_repo = FileCapabilityDefinitionRepository(tmp_path)
    urn = CapabilityURN.from_string("urn:karsa:capability:core:file-test:1.0.0")
    
    schema = ExecutionSchema(
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    
    definition = CapabilityDefinition(
        capability_id="cap_file_1",
        capability_family_id="fam_file_1",
        urn=urn,
        owner=CapabilityOwner("sys", "SYSTEM"),
        state=CapabilityLifecycleState.ACTIVE,
        schema_contract=schema,
        contract_fingerprint=ContractFingerprint.generate({"type": "object"}, {"type": "object"}),
        dependencies=[CapabilityDependency("dep_1", "urn:karsa:capability:core:dep:1.0.0")]
    )
    
    def_repo.save(definition)
    
    # Find active
    active = def_repo.find_active()
    assert len(active) == 1
    assert active[0].capability_id == "cap_file_1"
    assert len(active[0].dependencies) == 1
    assert active[0].dependencies[0].dependency_id == "dep_1"

    # Find by family
    family = def_repo.find_by_family("fam_file_1")
    assert len(family) == 1
    assert family[0].capability_id == "cap_file_1"
