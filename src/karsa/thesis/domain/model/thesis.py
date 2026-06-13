from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

class ThesisState(Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    RETIRED = "RETIRED"

class InvalidTransitionError(Exception):
    pass

class CircularDependencyError(Exception):
    pass

@dataclass
class ThesisVersion:
    version_id: str
    derived_from: Optional[str]
    created_at: datetime
    content_hash: str

@dataclass
class ThesisReview:
    review_id: str
    reviewer: str
    reviewed_at: datetime
    outcome: str
    notes: str

@dataclass
class ThesisInvalidationRule:
    rule_id: str
    metric_name: str
    threshold: float
    comparator: str  # e.g., ">", "<", "=="
    is_breached: bool = False

    def evaluate(self, value: float) -> bool:
        if self.comparator == ">":
            return value > self.threshold
        elif self.comparator == "<":
            return value < self.threshold
        elif self.comparator == ">=":
            return value >= self.threshold
        elif self.comparator == "<=":
            return value <= self.threshold
        elif self.comparator == "==":
            return value == self.threshold
        elif self.comparator == "!=":
            return value != self.threshold
        else:
            raise ValueError(f"Unknown comparator: {self.comparator}")

@dataclass
class ThesisDependencyEdge:
    dependency_thesis_id: str
    impact_weight: float
    description: str

@dataclass
class ThesisDependencyGraph:
    graph_id: str
    edges: List[ThesisDependencyEdge] = field(default_factory=list)

    def add_edge(self, edge: ThesisDependencyEdge) -> None:
        self.edges.append(edge)

    def check_cycles(self, get_dependencies_func) -> None:
        """
        get_dependencies_func: Callable[[str], List[str]]
        Returns a list of dependency_thesis_ids for a given thesis_id.
        """
        visited = set()
        stack = set()
        
        def dfs(current_id):
            if current_id in stack:
                raise CircularDependencyError(f"Circular dependency detected involving thesis: {current_id}")
            if current_id in visited:
                return
                
            visited.add(current_id)
            stack.add(current_id)
            
            deps = get_dependencies_func(current_id)
            for d in deps:
                dfs(d)
                
            stack.remove(current_id)
            
        # Start DFS from all edges of this graph
        for edge in self.edges:
            dfs(edge.dependency_thesis_id)

class ActiveThesis:
    def __init__(self, thesis_id: str, author: str, created_at: datetime):
        self.thesis_id = thesis_id
        self.author = author
        self.created_at = created_at
        self.state = ThesisState.ACTIVE
        self.versions: List[ThesisVersion] = []
        self.reviews: List[ThesisReview] = []
        self.invalidation_rules: List[ThesisInvalidationRule] = []
        self.dependency_graph: Optional[ThesisDependencyGraph] = None
        
    def degrade(self) -> None:
        if self.state not in [ThesisState.ACTIVE, ThesisState.CONFIRMED]:
            raise InvalidTransitionError(f"Cannot transition from {self.state} to DEGRADED")
        self.state = ThesisState.DEGRADED
        
    def request_review(self) -> None:
        if self.state not in [ThesisState.ACTIVE, ThesisState.DEGRADED, ThesisState.CONFIRMED]:
            raise InvalidTransitionError(f"Cannot transition from {self.state} to UNDER_REVIEW")
        self.state = ThesisState.UNDER_REVIEW

    def confirm(self, review: ThesisReview) -> None:
        if self.state != ThesisState.UNDER_REVIEW:
            raise InvalidTransitionError(f"Cannot transition from {self.state} to CONFIRMED. Must be UNDER_REVIEW")
        self.reviews.append(review)
        self.state = ThesisState.CONFIRMED
        
    def invalidate(self, reason: str) -> None:
        if self.state in [ThesisState.INVALIDATED, ThesisState.RETIRED]:
            raise InvalidTransitionError(f"Cannot invalidate from terminal state {self.state}")
        self.state = ThesisState.INVALIDATED
        
    def retire(self, reason: str) -> None:
        if self.state in [ThesisState.INVALIDATED, ThesisState.RETIRED]:
            raise InvalidTransitionError(f"Cannot retire from terminal state {self.state}")
        self.state = ThesisState.RETIRED

    def evaluate_telemetry(self, telemetry: dict) -> None:
        """Evaluate incoming telemetry. If any rule is breached, transition to DEGRADED."""
        breached = False
        for rule in self.invalidation_rules:
            if rule.metric_name in telemetry:
                if rule.evaluate(telemetry[rule.metric_name]):
                    rule.is_breached = True
                    breached = True
                else:
                    rule.is_breached = False
                    
        if breached and self.state in [ThesisState.ACTIVE, ThesisState.CONFIRMED]:
            self.degrade()
            
    def evaluate_dependencies(self, get_thesis_state_func) -> None:
        """
        Evaluate dependencies. If any are DEGRADED or INVALIDATED, degrade this thesis.
        get_thesis_state_func: Callable[[str], ThesisState]
        """
        if not self.dependency_graph:
            return
            
        degraded_count = 0
        for edge in self.dependency_graph.edges:
            dep_state = get_thesis_state_func(edge.dependency_thesis_id)
            if dep_state in [ThesisState.DEGRADED, ThesisState.INVALIDATED, ThesisState.RETIRED]:
                degraded_count += 1
                
        if degraded_count > 0 and self.state in [ThesisState.ACTIVE, ThesisState.CONFIRMED]:
            self.degrade()
