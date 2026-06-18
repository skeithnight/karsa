from karsa.attribution.domain.service.attribution_service import AttributionService
from karsa.attribution.domain.model.value_objects import PolicyInputSnapshot

def test_attribution_split_math():
    policy = PolicyInputSnapshot("v1", "ROLE_WEIGHTED", "REBASE", "BANKERS", "LEXI", {"AUTHOR": 0.6, "REFINER": 0.4}, 2)
    contributors = [{"target_id": "user1", "role": "AUTHOR"}, {"target_id": "user2", "role": "REFINER"}]
    
    allocations = AttributionService.calculate_allocations(100.0, "USD", contributors, policy)
    
    assert allocations[0].target_identity == "user1"
    assert allocations[0].attributed_pnl == 60.0
    assert allocations[1].target_identity == "user2"
    assert allocations[1].attributed_pnl == 40.0
