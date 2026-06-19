from karsa.shared.domain.event import DomainEvent

class AttributionCalculatedEvent(DomainEvent):
    def __init__(self, attribution_urn: str, review_urn: str, benchmark_urn: str, absolute_return: float, benchmark_return: float, true_alpha: float):
        super().__init__()
        self.payload = {
            "attribution_urn": attribution_urn,
            "review_urn": review_urn,
            "benchmark_urn": benchmark_urn,
            "absolute_return": absolute_return,
            "benchmark_return": benchmark_return,
            "true_alpha": true_alpha
        }

class CreditAllocatedEvent(DomainEvent):
    def __init__(self, attribution_urn: str, node_id: str, parent_node_id: str, subject_type: str, subject_urn: str, skill_ratio: float, luck_ratio: float):
        super().__init__()
        self.payload = {
            "attribution_urn": attribution_urn,
            "node_id": node_id,
            "parent_node_id": parent_node_id,
            "subject_type": subject_type,
            "subject_urn": subject_urn,
            "skill_ratio": skill_ratio,
            "luck_ratio": luck_ratio
        }
