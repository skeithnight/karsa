from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class ThesisVersionRecord:
    version_id: str
    derived_from: Optional[str]
    created_at: datetime
    content_hash: str

@dataclass
class ThesisReviewRecord:
    review_id: str
    reviewer: str
    reviewed_at: datetime
    outcome: str
    notes: str

@dataclass
class ThesisInvalidationRuleRecord:
    rule_id: str
    metric_name: str
    threshold: float
    comparator: str
    is_breached: bool

@dataclass
class ThesisDependencyEdgeRecord:
    dependency_thesis_id: str
    impact_weight: float
    description: str

@dataclass
class ThesisDependencyGraphRecord:
    graph_id: str
    edges: List[ThesisDependencyEdgeRecord] = field(default_factory=list)

@dataclass
class ThesisRecord:
    thesis_id: str
    author: str
    created_at: datetime
    state: str
    versions: List[ThesisVersionRecord] = field(default_factory=list)
    reviews: List[ThesisReviewRecord] = field(default_factory=list)
    invalidation_rules: List[ThesisInvalidationRuleRecord] = field(default_factory=list)
    dependency_graph: Optional[ThesisDependencyGraphRecord] = None
