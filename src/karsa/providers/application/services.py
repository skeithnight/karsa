from datetime import datetime, timezone
from typing import Any, Callable, List, Optional
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from karsa.providers.domain.repositories import ProviderDefinitionRepository, ProviderHealthStateRepository
from karsa.providers.domain.models import (
    ProviderDefinition, ProviderHealthState, ProviderURN, ProviderPricing, 
    ProviderCapabilityMapping, ProviderLifecycleState, ProviderHealthStatus,
    CapabilityRequirement, RoutingPolicy, ProviderRoutingDecision
)
from karsa.providers.domain.events import (
    ProviderRegisteredEvent, ProviderActivatedEvent, ProviderDeprecatedEvent,
    ProviderRetiredEvent, ProviderHealthChangedEvent, ProviderExecutionSucceededEvent,
    ProviderExecutionFailedEvent
)

class ProviderRegistryService:
    def __init__(
        self,
        definition_repo: ProviderDefinitionRepository,
        event_publisher: Optional[Callable[[Any], None]] = None
    ):
        self.definition_repo = definition_repo
        self.event_publisher = event_publisher

    def register_provider(
        self,
        provider_id: str,
        urn_str: str,
        pricing: ProviderPricing,
        mappings: Optional[List[ProviderCapabilityMapping]] = None
    ) -> ProviderDefinition:
        urn = ProviderURN.from_string(urn_str)

        if self.definition_repo.find_by_id(provider_id):
            raise ValueError(f"Provider with ID {provider_id} already exists.")
        if self.definition_repo.find_by_urn(urn):
            raise ValueError(f"Provider URN {urn_str} already exists.")

        provider = ProviderDefinition(
            provider_id=provider_id,
            provider_urn=urn,
            pricing=pricing,
            capability_mappings=mappings or []
        )
        self.definition_repo.save(provider)

        if self.event_publisher:
            event = ProviderRegisteredEvent(
                provider_id=provider.provider_id,
                provider_urn_str=provider.provider_urn.to_string(),
                input_rate=pricing.input_rate_per_1m,
                output_rate=pricing.output_rate_per_1m,
                timestamp=datetime.now(timezone.utc)
            )
            self.event_publisher(event)

        return provider

    def transition_provider_state(
        self,
        provider_id: str,
        new_state: ProviderLifecycleState,
        reason: str = ""
    ) -> None:
        provider = self.definition_repo.find_by_id(provider_id)
        if not provider:
            raise ValueError(f"Provider with ID {provider_id} not found.")

        old_state = provider.state
        provider.transition_to(new_state, reason)
        self.definition_repo.save(provider)

        if self.event_publisher:
            timestamp = datetime.now(timezone.utc)
            if new_state == ProviderLifecycleState.ACTIVE:
                self.event_publisher(ProviderActivatedEvent(provider_id=provider_id, reason=reason, timestamp=timestamp))
            elif new_state == ProviderLifecycleState.DEPRECATED:
                self.event_publisher(ProviderDeprecatedEvent(provider_id=provider_id, reason=reason, timestamp=timestamp))
            elif new_state == ProviderLifecycleState.RETIRED:
                self.event_publisher(ProviderRetiredEvent(provider_id=provider_id, reason=reason, timestamp=timestamp))


class ProviderTelemetryService:
    def __init__(
        self,
        health_repo: ProviderHealthStateRepository,
        event_publisher: Optional[Callable[[Any], None]] = None
    ):
        self.health_repo = health_repo
        self.event_publisher = event_publisher

    def process_execution_result(
        self,
        execution_id: str,
        workflow_id: str,
        provider_id: str,
        is_success: bool,
        latency_ms: float,
        error_message: str = "",
        error_type: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0
    ) -> None:
        health = self.health_repo.find_by_provider_id(provider_id)
        if not health:
            health = ProviderHealthState(provider_id=provider_id)

        timestamp = datetime.now(timezone.utc)
        if is_success:
            prev_status = health.record_success(latency_ms)
            self.health_repo.save(health)
            if self.event_publisher:
                self.event_publisher(ProviderExecutionSucceededEvent(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    provider_id=provider_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    duration_ms=int(latency_ms),
                    timestamp=timestamp
                ))
        else:
            prev_status = health.record_failure(latency_ms)
            self.health_repo.save(health)
            if self.event_publisher:
                self.event_publisher(ProviderExecutionFailedEvent(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    provider_id=provider_id,
                    error_message=error_message,
                    error_type=error_type,
                    duration_ms=int(latency_ms),
                    timestamp=timestamp
                ))

        if prev_status is not None and self.event_publisher:
            self.event_publisher(ProviderHealthChangedEvent(
                provider_id=provider_id,
                previous_status=prev_status.value,
                new_status=health.health_status.value,
                reason=f"Telemetry outcome is_success={is_success}",
                timestamp=timestamp
            ))


class ProviderRoutingService:
    def __init__(
        self,
        definition_repo: ProviderDefinitionRepository,
        health_repo: ProviderHealthStateRepository
    ):
        self.definition_repo = definition_repo
        self.health_repo = health_repo

    def resolve_route(
        self,
        capability_urn: str,
        requirements: CapabilityRequirement,
        policy: RoutingPolicy,
        replay_mode: bool = False,
        historical_selection: Optional[ProviderRoutingDecision] = None
    ) -> ProviderRoutingDecision:
        if replay_mode:
            if not historical_selection:
                raise ValueError("historical_selection must be provided in replay mode.")
            return historical_selection

        # Normal routing mode
        candidates = self.definition_repo.find_active_for_capability(capability_urn)
        
        # Filter active lifecycle candidates
        allowed_states = {
            ProviderLifecycleState.ACTIVE,
            ProviderLifecycleState.DEGRADED,
            ProviderLifecycleState.DEPRECATED
        }
        candidates = [c for c in candidates if c.state in allowed_states]

        # Evaluate capability requirements compatibility
        compatible_candidates = []
        for c in candidates:
            mapping = next((m for m in c.capability_mappings if m.capability_urn == capability_urn), None)
            if mapping and mapping.evaluate_compatibility(requirements):
                compatible_candidates.append(c)

        if not compatible_candidates:
            raise ValueError(f"No compatible provider found for capability {capability_urn}")

        # Fetch health states
        health_states = {}
        for c in compatible_candidates:
            health = self.health_repo.find_by_provider_id(c.provider_id)
            if not health:
                health = ProviderHealthState(provider_id=c.provider_id)
            health_states[c.provider_id] = health

        # Rank candidates based on policy
        # Sort key generator
        def sort_key(candidate: ProviderDefinition) -> tuple:
            health = health_states[candidate.provider_id]
            # Health status priority: ACTIVE (0) > DEGRADED (1) > SUSPENDED (2)
            health_priority = {
                ProviderHealthStatus.ACTIVE: 0,
                ProviderHealthStatus.DEGRADED: 1,
                ProviderHealthStatus.SUSPENDED: 2
            }.get(health.health_status, 0)

            # Cost ranking metric
            input_rate = candidate.pricing.input_rate_per_1m if candidate.pricing else 0.0
            output_rate = candidate.pricing.output_rate_per_1m if candidate.pricing else 0.0
            total_cost = input_rate + output_rate

            # Success rate calculation
            total_execs = health.success_count + health.failure_count
            success_rate = (health.success_count / total_execs) if total_execs > 0 else 1.0

            if policy == RoutingPolicy.LOWEST_COST:
                # 1. Cost 2. Health Priority 3. Latency
                return (total_cost, health_priority, health.average_latency_ms)
            elif policy == RoutingPolicy.LOWEST_LATENCY:
                # 1. Health Priority 2. Latency 3. Cost
                return (health_priority, health.average_latency_ms, total_cost)
            elif policy == RoutingPolicy.HIGHEST_HEALTH:
                # 1. Health Priority 2. Success Rate (descending, so negate) 3. Cost
                return (health_priority, -success_rate, total_cost)
            else:
                return (health_priority, total_cost, health.average_latency_ms)

        # Sort the compatible candidates
        sorted_candidates = sorted(compatible_candidates, key=sort_key)

        primary = sorted_candidates[0]
        fallbacks = [c.provider_urn.to_string() for c in sorted_candidates[1:] if c.provider_urn]

        estimated = primary.pricing.input_rate_per_1m if primary.pricing else 0.0

        return ProviderRoutingDecision(
            provider_id=primary.provider_id,
            provider_urn=primary.provider_urn.to_string() if primary.provider_urn else "",
            fallback_chain=fallbacks,
            routing_policy=policy,
            estimated_cost=estimated
        )
