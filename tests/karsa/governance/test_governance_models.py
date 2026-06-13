import pytest
from datetime import datetime, timezone, timedelta
from karsa.governance.domain.models import (
    PolicyURN, PolicyLifecycleState, PolicyDefinition, PolicyScope, PolicyRule,
    PolicyCondition, PolicyAction, GovernanceBudgetCache
)

# 1. Policy URN parsing
def test_policy_urn_valid_parsing():
    urn = PolicyURN.from_string("urn:karsa:policy:budget:max_cost:1.0.0")
    assert urn.namespace == "budget"
    assert urn.name == "max_cost"
    assert urn.version == "1.0.0"
    assert urn.to_string() == "urn:karsa:policy:budget:max_cost:1.0.0"

def test_policy_urn_invalid_parsing():
    invalid_urns = [
        "urn:karsa:capability:budget:max_cost:1.0.0",
        "urn:karsa:policy:budget:max_cost",
        "urn:karsa:policy::max_cost:1.0.0",
        "urn:karsa:policy:budget::1.0.0",
        "urn:karsa:policy:budget:max_cost:",
    ]
    for urn_str in invalid_urns:
        with pytest.raises(ValueError):
            PolicyURN.from_string(urn_str)


# 2. Policy Lifecycle FSM
def test_policy_lifecycle_valid_transitions():
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )
    assert policy.aggregate_version == 0

    # DRAFT -> REVIEW
    policy.transition_to(PolicyLifecycleState.REVIEW)
    assert policy.state == PolicyLifecycleState.REVIEW
    assert policy.aggregate_version == 1

    # REVIEW -> ACTIVE
    policy.transition_to(PolicyLifecycleState.ACTIVE)
    assert policy.state == PolicyLifecycleState.ACTIVE
    assert policy.aggregate_version == 2

    # ACTIVE -> SUSPENDED
    policy.transition_to(PolicyLifecycleState.SUSPENDED)
    assert policy.state == PolicyLifecycleState.SUSPENDED
    assert policy.aggregate_version == 3

    # SUSPENDED -> ACTIVE
    policy.transition_to(PolicyLifecycleState.ACTIVE)
    assert policy.state == PolicyLifecycleState.ACTIVE
    assert policy.aggregate_version == 4

    # ACTIVE -> REVOKED
    policy.transition_to(PolicyLifecycleState.REVOKED)
    assert policy.state == PolicyLifecycleState.REVOKED
    assert policy.aggregate_version == 5

    # REVOKED -> RETIRED
    policy.transition_to(PolicyLifecycleState.RETIRED)
    assert policy.state == PolicyLifecycleState.RETIRED
    assert policy.aggregate_version == 6

def test_policy_lifecycle_invalid_transitions():
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        state=PolicyLifecycleState.DRAFT
    )

    # Invalid: DRAFT directly to ACTIVE
    with pytest.raises(ValueError):
        policy.transition_to(PolicyLifecycleState.ACTIVE)

    policy.transition_to(PolicyLifecycleState.REVIEW)
    policy.transition_to(PolicyLifecycleState.RETIRED)

    # Invalid: RETIRED is terminal state
    with pytest.raises(ValueError):
        policy.transition_to(PolicyLifecycleState.ACTIVE)

def test_policy_definition_immutability():
    policy = PolicyDefinition(
        policy_id="pol-1",
        policy_urn=PolicyURN("budget", "max_cost", "1.0.0"),
        scope=PolicyScope("WORKFLOW", "*"),
        state=PolicyLifecycleState.DRAFT
    )

    # In DRAFT, modifications are allowed
    policy.priority = 50
    assert policy.priority == 50

    # Transition to ACTIVE
    policy.transition_to(PolicyLifecycleState.REVIEW)
    policy.transition_to(PolicyLifecycleState.ACTIVE)

    # In ACTIVE, configurations must be frozen
    with pytest.raises(ValueError):
        policy.priority = 200

    # Modifying rules list must be frozen too
    with pytest.raises(ValueError):
        policy.rules.append(PolicyRule(action=PolicyAction.DENY))


# 3. Budget Cache Staleness
def test_budget_cache_staleness():
    cache = GovernanceBudgetCache(workflow_id="wf-1", remaining_budget=10.0)
    assert cache.is_stale(max_stale_limit_seconds=60) is False

    # Mock age to 120 seconds in past
    cache.last_updated_at = datetime.now(timezone.utc) - timedelta(seconds=120)
    assert cache.is_stale(max_stale_limit_seconds=60) is True


# 4. Policy Condition Evaluation
def test_policy_condition_evaluation():
    cond = PolicyCondition(attribute="estimated_cost", operator="LESS_THAN_OR_EQUAL", value="0.05")
    assert cond.evaluate({"estimated_cost": 0.02}) is True
    assert cond.evaluate({"estimated_cost": 0.08}) is False
    assert cond.evaluate({"estimated_cost": "invalid"}) is False
    assert cond.evaluate({"some_other_key": 0.02}) is False
