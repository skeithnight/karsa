from karsa.attribution.domain.service.attribution_service import AttributionService
from karsa.attribution.domain.registry.policy_registry import AttributionPolicyRegistry

def test_attribution_service_calculate_allocations():
    policy = AttributionPolicyRegistry.get_policy("v1")
    
    # 2 contributors: AUTHOR (0.6 weight) and REFINER (0.2 weight)
    # Total weight: 0.8
    # Gross PNL: 100.00
    contributors = [
        {"target_id": "target-B", "role": "REFINER"},
        {"target_id": "target-A", "role": "AUTHOR"}
    ]
    
    allocations = AttributionService.calculate_allocations(
        gross_pnl=100.0,
        currency="USD",
        contributors=contributors,
        policy=policy
    )
    
    assert len(allocations) == 2
    # Lexicographical sort: target-A, then target-B
    assert allocations[0].target_identity == "target-A"
    assert allocations[0].gross_pnl == 100.0
    assert allocations[0].attribution_percentage == 0.6 / 0.8
    assert allocations[0].attributed_pnl == 75.00
    
    assert allocations[1].target_identity == "target-B"
    assert allocations[1].gross_pnl == 100.0
    assert allocations[1].attribution_percentage == 0.2 / 0.8
    assert allocations[1].attributed_pnl == 25.00

