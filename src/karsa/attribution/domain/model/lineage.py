from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from karsa.shared.domain.aggregate import VersionedAggregate

@dataclass(frozen=True)
class RecomputationLineage:
    """Tracks historical restatements and superseding chains for attribution audits."""
    session_id: str
    superseded_session_id: str
    recomputation_timestamp: datetime


def reconstruct_lineage_chain(records: list) -> str:
    """
    Deterministically reconstruct the lineage transitions for a set of records
    without using chronological sorting or timestamps.
    """
    superseded_map = {}
    invalidated_map = {}
    versions = set()
    
    for r in records:
        v = r.attribution_version
        versions.add(v)
        if r.superseded_by_version is not None:
            superseded_map[v] = r.superseded_by_version
        if r.invalidated_by_version is not None:
            invalidated_map[v] = r.invalidated_by_version
            
    if not versions:
        return ""
        
    current = min(versions)
    path = [f"Version {current}"]
    
    while True:
        if current in superseded_map:
            nxt = superseded_map[current]
            path.append(f"\u2192 superseded by Version {nxt}")
            current = nxt
        elif current in invalidated_map:
            nxt = invalidated_map[current]
            path.append(f"\u2192 invalidated by Version {nxt}")
            current = nxt
        else:
            break
            
    return "\n".join(path)


@dataclass
class LineageNode:
    """Entity representing a node-level capability path in a lineage graph."""
    node_id: str
    lineage_id: str
    capability_id: str
    worker_urn: str
    role: str

    def validate(self):
        if not self.node_id or not self.lineage_id or not self.capability_id:
            raise ValueError("node_id, lineage_id, and capability_id are required")


class DecisionLineage(VersionedAggregate):
    """Root aggregate tracking root decision causation graphs."""
    def __init__(
        self,
        lineage_id: str,
        decision_id: str,
        forecast_id: str,
        created_at: Optional[datetime] = None,
        nodes: Optional[List[LineageNode]] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.lineage_id = lineage_id
        self.decision_id = decision_id
        self.forecast_id = forecast_id
        self.created_at = created_at or datetime.utcnow()
        self.nodes = nodes or []
        self.validate()

    def validate(self):
        if not self.lineage_id:
            raise ValueError("lineage_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.forecast_id:
            raise ValueError("forecast_id is required")

    def add_node(self, node: LineageNode):
        if node.lineage_id != self.lineage_id:
            raise ValueError("Node belongs to a different lineage")
        node.validate()
        self.nodes.append(node)
        self.increment_version()
