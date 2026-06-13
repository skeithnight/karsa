from karsa.attribution.domain.model.value_objects import PolicyInputSnapshot

class AttributionPolicyRegistry:
    @staticmethod
    def get_policy(version: str) -> PolicyInputSnapshot:
        return PolicyInputSnapshot(
            policy_version="v1",
            weight_model="ROLE_WEIGHTED",
            normalization_strategy="REBASE_TO_ONE",
            rounding_strategy="BANKERS_ROUNDING",
            allocation_ordering="LEXICOGRAPHICAL_TARGET_ID",
            role_weights={"AUTHOR": 0.6, "REFINER": 0.2, "APPROVER": 0.2},
            currency_precision=2
        )
