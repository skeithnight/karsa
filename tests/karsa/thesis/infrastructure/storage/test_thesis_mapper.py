import pytest
from datetime import datetime, timezone
from karsa.thesis.domain.model.thesis import (
    ActiveThesis,
    ThesisVersion,
    ThesisReview,
    ThesisInvalidationRule,
    ThesisDependencyGraph,
    ThesisDependencyEdge,
    ThesisState
)
from karsa.thesis.infrastructure.storage.thesis_mapper import ThesisMapper

def test_mapper_roundtrip():
    thesis = ActiveThesis("T-1", "author1", datetime.now(timezone.utc))
    thesis.state = ThesisState.DEGRADED
    
    thesis.versions.append(ThesisVersion("v1", None, datetime.now(timezone.utc), "hash1"))
    thesis.reviews.append(ThesisReview("r1", "rev1", datetime.now(timezone.utc), "APPROVE", "notes"))
    thesis.invalidation_rules.append(ThesisInvalidationRule("rule1", "metric1", 10.0, ">", True))
    
    graph = ThesisDependencyGraph("g1")
    graph.add_edge(ThesisDependencyEdge("T-2", 0.5, "dep"))
    thesis.dependency_graph = graph
    
    # Domain -> Record
    record = ThesisMapper.to_record(thesis)
    assert record.thesis_id == "T-1"
    assert record.state == "DEGRADED"
    assert len(record.versions) == 1
    assert len(record.reviews) == 1
    assert len(record.invalidation_rules) == 1
    assert record.dependency_graph is not None
    assert len(record.dependency_graph.edges) == 1
    
    # Record -> Domain
    restored = ThesisMapper.to_domain(record)
    assert restored.thesis_id == "T-1"
    assert restored.state == ThesisState.DEGRADED
    assert len(restored.versions) == 1
    assert restored.versions[0].version_id == "v1"
    assert len(restored.reviews) == 1
    assert restored.reviews[0].review_id == "r1"
    assert len(restored.invalidation_rules) == 1
    assert restored.invalidation_rules[0].rule_id == "rule1"
    assert restored.invalidation_rules[0].is_breached is True
    assert restored.dependency_graph is not None
    assert restored.dependency_graph.graph_id == "g1"
    assert len(restored.dependency_graph.edges) == 1
    assert restored.dependency_graph.edges[0].dependency_thesis_id == "T-2"
