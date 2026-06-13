import pytest
from datetime import datetime, timezone
from karsa.providers.domain.models import (
    ProviderURN, ProviderLifecycleState, ProviderDefinition, ProviderPricing,
    ProviderCapabilityMapping, CapabilityRequirement
)

# 1. Provider URN tests
def test_provider_urn_valid_parsing():
    urn = ProviderURN.from_string("urn:karsa:provider:openai:gpt-4o:2024-05-13")
    assert urn.vendor == "openai"
    assert urn.model == "gpt-4o"
    assert urn.version == "2024-05-13"
    assert urn.to_string() == "urn:karsa:provider:openai:gpt-4o:2024-05-13"

def test_provider_urn_invalid_parsing():
    invalid_urns = [
        "urn:karsa:capability:openai:gpt-4o:2024-05-13",
        "urn:karsa:provider:openai:gpt-4o",
        "urn:karsa:provider::gpt-4o:2024-05-13",
        "urn:karsa:provider:openai::2024-05-13",
        "urn:karsa:provider:openai:gpt-4o:",
    ]
    for urn_str in invalid_urns:
        with pytest.raises(ValueError):
            ProviderURN.from_string(urn_str)


# 2. Lifecycle FSM tests
def test_provider_lifecycle_valid_transitions():
    provider = ProviderDefinition(
        provider_id="prov-1",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(5.0, 15.0),
        state=ProviderLifecycleState.DRAFT
    )
    assert provider.aggregate_version == 0

    # DRAFT -> REVIEW
    provider.transition_to(ProviderLifecycleState.REVIEW)
    assert provider.state == ProviderLifecycleState.REVIEW
    assert provider.aggregate_version == 1

    # REVIEW -> ACTIVE
    provider.transition_to(ProviderLifecycleState.ACTIVE)
    assert provider.state == ProviderLifecycleState.ACTIVE
    assert provider.aggregate_version == 2

    # ACTIVE -> DEGRADED
    provider.transition_to(ProviderLifecycleState.DEGRADED)
    assert provider.state == ProviderLifecycleState.DEGRADED
    assert provider.aggregate_version == 3

    # DEGRADED -> ACTIVE
    provider.transition_to(ProviderLifecycleState.ACTIVE)
    assert provider.state == ProviderLifecycleState.ACTIVE
    assert provider.aggregate_version == 4

    # ACTIVE -> DEPRECATED
    provider.transition_to(ProviderLifecycleState.DEPRECATED)
    assert provider.state == ProviderLifecycleState.DEPRECATED
    assert provider.aggregate_version == 5

    # DEPRECATED -> RETIRED
    provider.transition_to(ProviderLifecycleState.RETIRED)
    assert provider.state == ProviderLifecycleState.RETIRED
    assert provider.aggregate_version == 6

def test_provider_lifecycle_invalid_transitions():
    provider = ProviderDefinition(
        provider_id="prov-1",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(5.0, 15.0),
        state=ProviderLifecycleState.DRAFT
    )

    # Invalid: DRAFT directly to ACTIVE
    with pytest.raises(ValueError):
        provider.transition_to(ProviderLifecycleState.ACTIVE)

    provider.transition_to(ProviderLifecycleState.REVIEW)
    provider.transition_to(ProviderLifecycleState.RETIRED)

    # Invalid: RETIRED is terminal state
    with pytest.raises(ValueError):
        provider.transition_to(ProviderLifecycleState.ACTIVE)

def test_provider_definition_immutability():
    provider = ProviderDefinition(
        provider_id="prov-1",
        provider_urn=ProviderURN("openai", "gpt-4o", "v1"),
        pricing=ProviderPricing(5.0, 15.0),
        state=ProviderLifecycleState.DRAFT
    )

    # In DRAFT, modification is allowed
    provider.pricing = ProviderPricing(10.0, 20.0)
    assert provider.pricing.input_rate_per_1m == 10.0

    # Transition to ACTIVE
    provider.transition_to(ProviderLifecycleState.REVIEW)
    provider.transition_to(ProviderLifecycleState.ACTIVE)

    # In ACTIVE, configuration modification must be blocked
    with pytest.raises(ValueError):
        provider.pricing = ProviderPricing(2.0, 4.0)

    # Modification of list must be blocked
    with pytest.raises(ValueError):
        provider.capability_mappings.append(ProviderCapabilityMapping(capability_urn="urn:karsa:capability:test:test:1.0.0"))


# 3. Capability Compatibility tests
def test_capability_mapping_compatibility_success():
    mapping = ProviderCapabilityMapping(
        capability_urn="urn:karsa:capability:core:chat:1.0.0",
        json_mode=True,
        tool_calling=True,
        streaming=True,
        context_window=16384,
        structured_output=True,
        reasoning_support=False
    )

    req = CapabilityRequirement(
        json_mode=True,
        tool_calling=True,
        streaming=True,
        structured_output=True,
        reasoning_support=False,
        min_context_window=8192
    )
    assert mapping.evaluate_compatibility(req) is True

def test_capability_mapping_compatibility_failure():
    mapping = ProviderCapabilityMapping(
        capability_urn="urn:karsa:capability:core:chat:1.0.0",
        json_mode=False,  # no json mode support
        tool_calling=True,
        streaming=True,
        context_window=8192,
        structured_output=True,
        reasoning_support=False
    )

    # Requires json_mode
    req = CapabilityRequirement(
        json_mode=True,
        tool_calling=True,
        streaming=True,
        structured_output=True,
        reasoning_support=False,
        min_context_window=8192
    )
    assert mapping.evaluate_compatibility(req) is False

    # Requires larger context window
    mapping2 = ProviderCapabilityMapping(
        capability_urn="urn:karsa:capability:core:chat:1.0.0",
        json_mode=True,
        tool_calling=True,
        streaming=True,
        context_window=8192,
        structured_output=True,
        reasoning_support=False
    )
    req2 = CapabilityRequirement(
        json_mode=True,
        tool_calling=True,
        streaming=True,
        structured_output=True,
        reasoning_support=False,
        min_context_window=16384
    )
    assert mapping2.evaluate_compatibility(req2) is False
