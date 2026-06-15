import pytest
from pathlib import Path
from datetime import datetime, timezone
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.providers.domain.models import (
    ProviderURN, ProviderLifecycleState, ProviderDefinition, ProviderPricing,
    ProviderCapabilityMapping, CapabilityRequirement, RoutingPolicy,
    ProviderHealthStatus, ProviderHealthState, ProviderRoutingDecision
)
from karsa.providers.infrastructure.repositories import (
    InMemoryProviderDefinitionRepository, InMemoryProviderHealthStateRepository,
    FileProviderDefinitionRepository, FileProviderHealthStateRepository
)
from karsa.providers.application.services import (
    ProviderRegistryService, ProviderTelemetryService, ProviderRoutingService
)

@pytest.fixture
def memory_repos():
    return InMemoryProviderDefinitionRepository(), InMemoryProviderHealthStateRepository()

@pytest.fixture
def file_repos(tmp_path):
    return FileProviderDefinitionRepository(tmp_path), FileProviderHealthStateRepository(tmp_path)


# 4. Routing tests
def test_routing_lowest_cost(memory_repos):
    def_repo, health_repo = memory_repos
    
    # Register candidate A (cheap, slower)
    p_a = ProviderDefinition(
        provider_id="prov-a",
        provider_urn=ProviderURN("openai", "gpt-4o-mini", "v1"),
        pricing=ProviderPricing(0.15, 0.60),
        state=ProviderLifecycleState.ACTIVE,
        capability_mappings=[
            ProviderCapabilityMapping(capability_urn="urn:karsa:capability:chat:v1", context_window=8192)
        ]
    )
    def_repo.save(p_a)
    h_a = ProviderHealthState(provider_id="prov-a", health_status=ProviderHealthStatus.ACTIVE)
    h_a.record_success(500.0) # 500ms latency
    health_repo.save(h_a)

    # Register candidate B (expensive, faster)
    p_b = ProviderDefinition(
        provider_id="prov-b",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(5.0, 15.0),
        state=ProviderLifecycleState.ACTIVE,
        capability_mappings=[
            ProviderCapabilityMapping(capability_urn="urn:karsa:capability:chat:v1", context_window=8192)
        ]
    )
    def_repo.save(p_b)
    h_b = ProviderHealthState(provider_id="prov-b", health_status=ProviderHealthStatus.ACTIVE)
    h_b.record_success(100.0) # 100ms latency
    health_repo.save(h_b)

    routing_service = ProviderRoutingService(def_repo, health_repo)
    req = CapabilityRequirement(
        json_mode=True, tool_calling=True, streaming=True,
        structured_output=True, reasoning_support=False, min_context_window=4096
    )

    # Policy: LOWEST_COST -> should select prov-a
    decision = routing_service.resolve_route(
        capability_urn="urn:karsa:capability:chat:v1",
        requirements=req,
        policy=RoutingPolicy.LOWEST_COST
    )
    assert decision.provider_id == "prov-a"
    assert decision.provider_urn == "urn:karsa:provider:openai:gpt-4o-mini:v1"
    assert decision.fallback_chain == ["urn:karsa:provider:openai:gpt-4o:v1"]
    assert decision.estimated_cost == 0.15

def test_routing_lowest_latency(memory_repos):
    def_repo, health_repo = memory_repos
    
    p_a = ProviderDefinition(
        provider_id="prov-a",
        provider_urn=ProviderURN("openai", "gpt-4o-mini", "v1"),
        pricing=ProviderPricing(0.15, 0.60),
        state=ProviderLifecycleState.ACTIVE,
        capability_mappings=[
            ProviderCapabilityMapping(capability_urn="urn:karsa:capability:chat:v1", context_window=8192)
        ]
    )
    def_repo.save(p_a)
    h_a = ProviderHealthState(provider_id="prov-a", health_status=ProviderHealthStatus.ACTIVE)
    h_a.record_success(500.0)
    health_repo.save(h_a)

    p_b = ProviderDefinition(
        provider_id="prov-b",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(5.0, 15.0),
        state=ProviderLifecycleState.ACTIVE,
        capability_mappings=[
            ProviderCapabilityMapping(capability_urn="urn:karsa:capability:chat:v1", context_window=8192)
        ]
    )
    def_repo.save(p_b)
    h_b = ProviderHealthState(provider_id="prov-b", health_status=ProviderHealthStatus.ACTIVE)
    h_b.record_success(100.0)
    health_repo.save(h_b)

    routing_service = ProviderRoutingService(def_repo, health_repo)
    req = CapabilityRequirement(
        json_mode=True, tool_calling=True, streaming=True,
        structured_output=True, reasoning_support=False, min_context_window=4096
    )

    # Policy: LOWEST_LATENCY -> should select prov-b
    decision = routing_service.resolve_route(
        capability_urn="urn:karsa:capability:chat:v1",
        requirements=req,
        policy=RoutingPolicy.LOWEST_LATENCY
    )
    assert decision.provider_id == "prov-b"
    assert decision.fallback_chain == ["urn:karsa:provider:openai:gpt-4o-mini:v1"]

def test_routing_highest_health(memory_repos):
    def_repo, health_repo = memory_repos
    
    p_a = ProviderDefinition(
        provider_id="prov-a",
        provider_urn=ProviderURN("openai", "gpt-4o-mini", "v1"),
        pricing=ProviderPricing(0.15, 0.60),
        state=ProviderLifecycleState.ACTIVE,
        capability_mappings=[
            ProviderCapabilityMapping(capability_urn="urn:karsa:capability:chat:v1", context_window=8192)
        ]
    )
    def_repo.save(p_a)
    # prov-a is degraded (e.g. failures occurred)
    h_a = ProviderHealthState(provider_id="prov-a", health_status=ProviderHealthStatus.DEGRADED)
    h_a.record_failure(100.0)
    h_a.record_failure(100.0)
    h_a.record_failure(100.0)
    health_repo.save(h_a)

    p_b = ProviderDefinition(
        provider_id="prov-b",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(5.0, 15.0),
        state=ProviderLifecycleState.ACTIVE,
        capability_mappings=[
            ProviderCapabilityMapping(capability_urn="urn:karsa:capability:chat:v1", context_window=8192)
        ]
    )
    def_repo.save(p_b)
    # prov-b is active/healthy
    h_b = ProviderHealthState(provider_id="prov-b", health_status=ProviderHealthStatus.ACTIVE)
    health_repo.save(h_b)

    routing_service = ProviderRoutingService(def_repo, health_repo)
    req = CapabilityRequirement(
        json_mode=True, tool_calling=True, streaming=True,
        structured_output=True, reasoning_support=False, min_context_window=4096
    )

    # Policy: HIGHEST_HEALTH -> should select prov-b (since prov-a is DEGRADED)
    decision = routing_service.resolve_route(
        capability_urn="urn:karsa:capability:chat:v1",
        requirements=req,
        policy=RoutingPolicy.HIGHEST_HEALTH
    )
    assert decision.provider_id == "prov-b"
    assert decision.fallback_chain == ["urn:karsa:provider:openai:gpt-4o-mini:v1"]


# 5. Telemetry tests
def test_telemetry_success_tracking(memory_repos):
    def_repo, health_repo = memory_repos
    telemetry_service = ProviderTelemetryService(health_repo)

    telemetry_service.process_execution_result(
        execution_id="exec-1",
        workflow_id="wf-1",
        provider_id="prov-1",
        is_success=True,
        latency_ms=250.0
    )

    health = health_repo.find_by_provider_id("prov-1")
    assert health is not None
    assert health.success_count == 1
    assert health.failure_count == 0
    assert health.average_latency_ms == 250.0
    assert health.consecutive_failures == 0
    assert health.health_status == ProviderHealthStatus.ACTIVE

def test_telemetry_failure_tracking_degradation_and_recovery(memory_repos):
    def_repo, health_repo = memory_repos
    telemetry_service = ProviderTelemetryService(health_repo)

    # Record 3 failures -> should transition to DEGRADED
    for i in range(3):
        telemetry_service.process_execution_result(
            execution_id=f"exec-fail-{i}",
            workflow_id="wf-1",
            provider_id="prov-1",
            is_success=False,
            latency_ms=100.0
        )

    health = health_repo.find_by_provider_id("prov-1")
    assert health.failure_count == 3
    assert health.consecutive_failures == 3
    assert health.health_status == ProviderHealthStatus.DEGRADED

    # Record 2 more failures (total 5) -> should transition to SUSPENDED
    for i in range(3, 5):
        telemetry_service.process_execution_result(
            execution_id=f"exec-fail-{i}",
            workflow_id="wf-1",
            provider_id="prov-1",
            is_success=False,
            latency_ms=100.0
        )

    health = health_repo.find_by_provider_id("prov-1")
    assert health.consecutive_failures == 5
    assert health.health_status == ProviderHealthStatus.SUSPENDED

    # Record 1 success -> should recover to ACTIVE
    telemetry_service.process_execution_result(
        execution_id="exec-success",
        workflow_id="wf-1",
        provider_id="prov-1",
        is_success=True,
        latency_ms=80.0
    )

    health = health_repo.find_by_provider_id("prov-1")
    assert health.consecutive_failures == 0
    assert health.health_status == ProviderHealthStatus.ACTIVE
    assert health.success_count == 1


# 6. Repositories tests
def test_in_memory_persistence_and_occ(memory_repos):
    def_repo, health_repo = memory_repos

    # Define
    p = ProviderDefinition(
        provider_id="prov-1",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(1.0, 2.0),
        state=ProviderLifecycleState.DRAFT
    )
    def_repo.save(p)

    loaded = def_repo.find_by_id("prov-1")
    assert loaded.aggregate_version == 0
    assert loaded.state == ProviderLifecycleState.DRAFT

    # Transition loaded copy
    loaded.transition_to(ProviderLifecycleState.REVIEW)
    def_repo.save(loaded)  # Saved version is 1, which is stored_version (0) + 1. Correct.

    # Modify original copy (which has version 0) and try to save -> should raise OCC error
    p.pricing = ProviderPricing(5.0, 10.0)
    with pytest.raises(ConcurrencyConflictError):
        def_repo.save(p)

def test_file_persistence_and_occ(file_repos):
    def_repo, health_repo = file_repos

    p = ProviderDefinition(
        provider_id="prov-1",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(1.0, 2.0),
        state=ProviderLifecycleState.DRAFT
    )
    def_repo.save(p)

    # Verify files created on disk
    path = def_repo.base_dir / "prov-1.json"
    assert path.exists()

    loaded = def_repo.find_by_id("prov-1")
    assert loaded.aggregate_version == 0

    # Transition loaded
    loaded.transition_to(ProviderLifecycleState.REVIEW)
    def_repo.save(loaded)

    # Save original (stale) version -> should raise ConcurrencyConflictError
    with pytest.raises(ConcurrencyConflictError):
        def_repo.save(p)


# 7. Replay tests
def test_replay_bypass(memory_repos):
    def_repo, health_repo = memory_repos
    routing_service = ProviderRoutingService(def_repo, health_repo)

    historical = ProviderRoutingDecision(
        provider_id="historical-id",
        provider_urn="urn:karsa:provider:openai:gpt-historical:v1",
        fallback_chain=[],
        routing_policy=RoutingPolicy.LOWEST_COST,
        estimated_cost=0.0
    )

    # In replay mode, routing service must directly return the historical decision
    decision = routing_service.resolve_route(
        capability_urn="urn:karsa:capability:chat:v1",
        requirements=None,
        policy=RoutingPolicy.LOWEST_LATENCY,
        replay_mode=True,
        historical_selection=historical
    )
    assert decision == historical
    assert decision.provider_id == "historical-id"
    assert decision.provider_urn == "urn:karsa:provider:openai:gpt-historical:v1"


# 8. Aggregate Boundary tests
def test_aggregate_boundaries_isolation(memory_repos):
    def_repo, health_repo = memory_repos
    
    # Registry service uses definition_repo only
    registry = ProviderRegistryService(def_repo)
    # Telemetry service uses health_repo only
    telemetry = ProviderTelemetryService(health_repo)

    # Register provider
    registry.register_provider(
        provider_id="prov-1",
        urn_str="urn:karsa:provider:openai:gpt-4o:v1",
        pricing=ProviderPricing(5.0, 15.0)
    )

    # ProviderDefinition exists, but no ProviderHealthState has been created yet
    assert def_repo.find_by_id("prov-1") is not None
    assert health_repo.find_by_provider_id("prov-1") is None

    # Telemetry executes -> creates health state
    telemetry.process_execution_result(
        execution_id="exec-1",
        workflow_id="wf-1",
        provider_id="prov-1",
        is_success=True,
        latency_ms=100.0
    )

    # Verify that telemetry updated health state but did NOT modify ProviderDefinition configuration
    health = health_repo.find_by_provider_id("prov-1")
    assert health is not None
    assert health.success_count == 1
    
    definition = def_repo.find_by_id("prov-1")
    assert definition.aggregate_version == 0  # Still 0, definition aggregate was not written to or mutated.


def test_custom_health_thresholds(memory_repos):
    def_repo, health_repo = memory_repos
    telemetry_service = ProviderTelemetryService(health_repo)

    # Initialize a custom health state with non-default thresholds
    custom_health = ProviderHealthState(
        provider_id="prov-custom",
        degraded_threshold=1,
        suspended_threshold=2
    )
    health_repo.save(custom_health)

    # First failure -> should transition to DEGRADED immediately (threshold = 1)
    telemetry_service.process_execution_result(
        execution_id="exec-fail-1",
        workflow_id="wf-1",
        provider_id="prov-custom",
        is_success=False,
        latency_ms=100.0
    )
    health = health_repo.find_by_provider_id("prov-custom")
    assert health.health_status == ProviderHealthStatus.DEGRADED

    # Second failure -> should transition to SUSPENDED immediately (threshold = 2)
    telemetry_service.process_execution_result(
        execution_id="exec-fail-2",
        workflow_id="wf-1",
        provider_id="prov-custom",
        is_success=False,
        latency_ms=100.0
    )
    health = health_repo.find_by_provider_id("prov-custom")
    assert health.health_status == ProviderHealthStatus.SUSPENDED

