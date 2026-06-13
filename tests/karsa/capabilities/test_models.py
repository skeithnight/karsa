import pytest
from datetime import datetime, timezone
from karsa.capabilities.domain.models import (
    CapabilityURN, CapabilityOwner, ExecutionSchema, ExecutionBudget,
    CapabilityDefinition, CapabilityExecution, CapabilityLifecycleState,
    ExecutionStatus, ExecutionTelemetry, ContractFingerprint, CapabilityDependency,
    ExecutionContract
)

def test_capability_urn_valid():
    urn = CapabilityURN.from_string("urn:karsa:capability:core:docker-execution:v1.0.0")
    assert urn.namespace == "core"
    assert urn.name == "docker-execution"
    assert urn.version == "v1.0.0"
    assert urn.to_string() == "urn:karsa:capability:core:docker-execution:v1.0.0"

def test_capability_urn_invalid():
    with pytest.raises(ValueError):
        CapabilityURN.from_string("invalid:urn:karsa:capability:core:docker:v1")
    with pytest.raises(ValueError):
        CapabilityURN.from_string("urn:karsa:capability:core")

def test_contract_validation():
    input_schema = {
        "type": "object",
        "properties": {"cmd": {"type": "string"}},
        "required": ["cmd"]
    }
    output_schema = {
        "type": "object",
        "properties": {"exit_code": {"type": "integer"}},
        "required": ["exit_code"]
    }
    
    schema_contract = ExecutionSchema(input_schema=input_schema, output_schema=output_schema)
    definition = CapabilityDefinition(
        capability_id="cap_1",
        capability_family_id="fam_1",
        urn=CapabilityURN.from_string("urn:karsa:capability:core:test:v1.0.0"),
        schema_contract=schema_contract
    )
    
    # Valid input
    definition.validate_input({"cmd": "ls"})
    # Invalid input
    with pytest.raises(ValueError):
        definition.validate_input({"command": "ls"})
        
    # Valid output
    definition.validate_output({"exit_code": 0})
    # Invalid output
    with pytest.raises(ValueError):
        definition.validate_output({"exit_code": "success"})

def test_fingerprint_generation():
    input_schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    output_schema = {"type": "object", "properties": {"b": {"type": "integer"}}}
    
    # Generate fingerprint
    fp1 = ContractFingerprint.generate(input_schema, output_schema)
    
    # Shuffle keys in schema to check normalization
    input_schema_shuffled = {"properties": {"a": {"type": "string"}}, "type": "object"}
    fp2 = ContractFingerprint.generate(input_schema_shuffled, output_schema)
    
    assert fp1.sha256_hash == fp2.sha256_hash
    
    # Modifying properties changes fingerprint
    input_schema_modified = {"type": "object", "properties": {"a": {"type": "integer"}}}
    fp3 = ContractFingerprint.generate(input_schema_modified, output_schema)
    assert fp1.sha256_hash != fp3.sha256_hash

def test_definition_lifecycle():
    urn = CapabilityURN.from_string("urn:karsa:capability:core:docker-execution:v1.0.0")
    owner = CapabilityOwner(owner_id="sys", owner_type="SYSTEM")
    
    definition = CapabilityDefinition(
        capability_id="cap_1",
        capability_family_id="fam_1",
        urn=urn,
        owner=owner,
        state=CapabilityLifecycleState.DRAFT
    )
    
    assert definition.state == CapabilityLifecycleState.DRAFT
    assert definition.aggregate_version == 0
    
    # Transition to REVIEW
    definition.transition_to(CapabilityLifecycleState.REVIEW)
    assert definition.state == CapabilityLifecycleState.REVIEW
    assert definition.aggregate_version == 1
    
    # Transition to ACTIVE
    definition.transition_to(CapabilityLifecycleState.ACTIVE)
    assert definition.state == CapabilityLifecycleState.ACTIVE
    
    # Transition to SUSPENDED
    definition.transition_to(CapabilityLifecycleState.SUSPENDED)
    assert definition.state == CapabilityLifecycleState.SUSPENDED
    
    # Back to ACTIVE
    definition.transition_to(CapabilityLifecycleState.ACTIVE)
    assert definition.state == CapabilityLifecycleState.ACTIVE
    
    # Transition to REVOKED
    definition.transition_to(CapabilityLifecycleState.REVOKED)
    assert definition.state == CapabilityLifecycleState.REVOKED
    
    # Terminal state check
    with pytest.raises(ValueError):
        definition.transition_to(CapabilityLifecycleState.ACTIVE)

def test_execution_transitions():
    urn = CapabilityURN.from_string("urn:karsa:capability:core:docker-execution:v1.0.0")
    budget = ExecutionBudget()
    
    execution = CapabilityExecution(
        execution_id="exec_1",
        capability_urn=urn,
        correlation_id="corr_1",
        causation_id="caus_1",
        workspace_id="ws_1",
        branch_id="br_1",
        status=ExecutionStatus.QUEUED,
        budget=budget,
        input_payload={"cmd": "ls"}
    )
    
    assert execution.status == ExecutionStatus.QUEUED
    
    # Invalid transition (complete without start)
    telemetry = ExecutionTelemetry(duration_ms=10)
    with pytest.raises(ValueError):
        execution.complete({"exit_code": 0}, telemetry)
        
    # Valid flow
    execution.start()
    assert execution.status == ExecutionStatus.RUNNING
    
    execution.complete({"exit_code": 0}, telemetry)
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.output_payload == {"exit_code": 0}

def test_capability_definition_immutability():
    # 1. Setup Draft Capability
    urn1 = CapabilityURN.from_string("urn:karsa:capability:core:docker-execution:v1.0.0")
    urn2 = CapabilityURN.from_string("urn:karsa:capability:core:docker-execution:v2.0.0")
    owner = CapabilityOwner(owner_id="sys", owner_type="SYSTEM")
    schema = ExecutionSchema(input_schema={}, output_schema={})
    
    definition = CapabilityDefinition(
        capability_id="cap_1",
        capability_family_id="fam_1",
        urn=urn1,
        owner=owner,
        state=CapabilityLifecycleState.DRAFT,
        schema_contract=schema
    )
    
    # DRAFT operations must succeed
    definition.urn = urn2
    assert definition.urn == urn2
    
    definition.dependencies.append(CapabilityDependency("dep_1", "urn:karsa:capability:core:dep:1.0.0"))
    assert len(definition.dependencies) == 1
    
    # 2. Transition to ACTIVE
    definition.transition_to(CapabilityLifecycleState.REVIEW)
    definition.transition_to(CapabilityLifecycleState.ACTIVE)
    
    # ACTIVE operations must fail
    # A) definition.urn = ... must fail
    with pytest.raises(ValueError):
        definition.urn = urn1
        
    # B) definition.dependencies.append(...) must fail
    with pytest.raises(ValueError):
        definition.dependencies.append(CapabilityDependency("dep_2", "urn:karsa:capability:core:dep:2.0.0"))
        
    # C) definition.contract = ... must fail (AttributeError since it has no setter)
    with pytest.raises(AttributeError):
        definition.contract = ExecutionContract({}, {})
        
    # E) Replay safety: verifying that we cannot bypass this by direct mutation
    # Any attempt to write to attributes triggers ValueError
    with pytest.raises(ValueError):
        definition.schema_contract = ExecutionSchema({}, {})
