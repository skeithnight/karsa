from dataclasses import dataclass, field
from typing import List, Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.attribution.domain.events import (
    AttributionCalculatedEvent, CreditAllocatedEvent
)

@dataclass
class AttributionSubject:
    subject_type: str
    subject_urn: str

@dataclass
class CreditNode:
    node_id: str
    parent_node_id: Optional[str]
    subject: AttributionSubject
    skill_ratio: float
    luck_ratio: float

class AttributionLedger(VersionedAggregate):
    def __init__(self, aggregate_version: int = 1):
        super().__init__(aggregate_version)
        self.attribution_urn: str = ""
        self.review_urn: str = ""
        self.benchmark_urn: str = ""
        self.absolute_return: float = 0.0
        self.benchmark_return: float = 0.0
        self.true_alpha: float = 0.0
        self.nodes: List[CreditNode] = []

    @property
    def aggregate_id(self) -> str:
        return self.attribution_urn

    @classmethod
    def calculate(cls, attribution_urn: str, review_urn: str, benchmark_urn: str, absolute_return: float, benchmark_return: float) -> "AttributionLedger":
        ledger = cls(aggregate_version=1)
        ledger.attribution_urn = attribution_urn
        ledger.review_urn = review_urn
        ledger.benchmark_urn = benchmark_urn
        ledger.absolute_return = absolute_return
        ledger.benchmark_return = benchmark_return
        ledger.true_alpha = absolute_return - benchmark_return
        
        event = AttributionCalculatedEvent(
            attribution_urn=attribution_urn,
            review_urn=review_urn,
            benchmark_urn=benchmark_urn,
            absolute_return=absolute_return,
            benchmark_return=benchmark_return,
            true_alpha=ledger.true_alpha
        )
        ledger.record_event(event)
        return ledger

    def allocate_credit(self, node_id: str, parent_node_id: Optional[str], subject: AttributionSubject, skill_ratio: float, luck_ratio: float):
        # Validation: check parent node if provided
        if parent_node_id:
            parent = next((n for n in self.nodes if n.node_id == parent_node_id), None)
            if not parent:
                raise ValueError(f"Parent node {parent_node_id} not found")
            
            # Simplified validation: child cannot exceed parent's total allocation ratio.
            # In a real system, sum of children's ratios shouldn't exceed parent.
            if skill_ratio + luck_ratio > parent.skill_ratio + parent.luck_ratio:
                raise ValueError("Child allocation exceeds parent allocation")
        else:
            # Root node validation: sum of root nodes shouldn't exceed 1.0 (100%)
            root_allocated = sum(n.skill_ratio + n.luck_ratio for n in self.nodes if not n.parent_node_id)
            if root_allocated + skill_ratio + luck_ratio > 1.0:
                raise ValueError("Root allocations exceed 100%")

        node = CreditNode(node_id, parent_node_id, subject, skill_ratio, luck_ratio)
        self.nodes.append(node)
        
        event = CreditAllocatedEvent(
            attribution_urn=self.attribution_urn,
            node_id=node_id,
            parent_node_id=parent_node_id,
            subject_type=subject.subject_type,
            subject_urn=subject.subject_urn,
            skill_ratio=skill_ratio,
            luck_ratio=luck_ratio
        )
        self.record_event(event)

    def apply_event(self, event):
        if isinstance(event, AttributionCalculatedEvent):
            self.attribution_urn = event.payload["attribution_urn"]
            self.review_urn = event.payload["review_urn"]
            self.benchmark_urn = event.payload["benchmark_urn"]
            self.absolute_return = event.payload["absolute_return"]
            self.benchmark_return = event.payload["benchmark_return"]
            self.true_alpha = event.payload["true_alpha"]
        elif isinstance(event, CreditAllocatedEvent):
            self.nodes.append(CreditNode(
                event.payload["node_id"],
                event.payload["parent_node_id"],
                AttributionSubject(event.payload["subject_type"], event.payload["subject_urn"]),
                event.payload["skill_ratio"],
                event.payload["luck_ratio"]
            ))
        self.increment_version()
