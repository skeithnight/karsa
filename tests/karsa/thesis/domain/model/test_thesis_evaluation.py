import pytest
from datetime import datetime, timezone
from karsa.thesis.domain.model.thesis import (
    ActiveThesis, 
    ThesisState, 
    ThesisInvalidationRule,
    ThesisDependencyGraph,
    ThesisDependencyEdge,
    CircularDependencyError
)

def test_invalidation_rule_evaluation():
    rule_gt = ThesisInvalidationRule("r1", "volatility", 0.5, ">")
    assert rule_gt.evaluate(0.6) is True
    assert rule_gt.evaluate(0.4) is False
    
    rule_lt = ThesisInvalidationRule("r2", "price", 100.0, "<")
    assert rule_lt.evaluate(90.0) is True
    assert rule_lt.evaluate(110.0) is False
    
    rule_eq = ThesisInvalidationRule("r3", "status", 1.0, "==")
    assert rule_eq.evaluate(1.0) is True
    assert rule_eq.evaluate(0.0) is False

def test_active_to_degraded_on_breach():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    rule = ThesisInvalidationRule("r1", "volatility", 0.5, ">")
    thesis.invalidation_rules.append(rule)
    
    # Below threshold, shouldn't degrade
    thesis.evaluate_telemetry({"volatility": 0.4})
    assert thesis.state == ThesisState.ACTIVE
    assert rule.is_breached is False
    
    # Above threshold, should degrade
    thesis.evaluate_telemetry({"volatility": 0.6})
    assert thesis.state == ThesisState.DEGRADED
    assert rule.is_breached is True

def test_missing_telemetry_ignored():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    rule = ThesisInvalidationRule("r1", "volatility", 0.5, ">")
    thesis.invalidation_rules.append(rule)
    
    # Missing metric, shouldn't degrade
    thesis.evaluate_telemetry({"other_metric": 0.8})
    assert thesis.state == ThesisState.ACTIVE
    assert rule.is_breached is False

def test_dependency_degradation_propagation():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    graph = ThesisDependencyGraph("g1")
    graph.add_edge(ThesisDependencyEdge("T-2", 1.0, "Relies on macro thesis"))
    thesis.dependency_graph = graph
    
    # Mock dependency states
    dep_states = {"T-2": ThesisState.ACTIVE}
    def get_state(tid):
        return dep_states.get(tid, ThesisState.ACTIVE)
        
    thesis.evaluate_dependencies(get_state)
    assert thesis.state == ThesisState.ACTIVE
    
    # Degrade dependency
    dep_states["T-2"] = ThesisState.DEGRADED
    thesis.evaluate_dependencies(get_state)
    assert thesis.state == ThesisState.DEGRADED

def test_empty_dependency_graph():
    thesis = ActiveThesis("T-1", "quant_1", datetime.now(timezone.utc))
    graph = ThesisDependencyGraph("g1")
    thesis.dependency_graph = graph
    
    thesis.evaluate_dependencies(lambda tid: ThesisState.ACTIVE)
    assert thesis.state == ThesisState.ACTIVE

def test_circular_dependency_detection():
    graph = ThesisDependencyGraph("g1")
    graph.add_edge(ThesisDependencyEdge("T-2", 1.0, "Relies on T-2"))
    
    # T-1 -> T-2 -> T-3 -> T-1
    dep_map = {
        "T-1": ["T-2"],
        "T-2": ["T-3"],
        "T-3": ["T-1"]
    }
    
    def get_deps(tid):
        return dep_map.get(tid, [])
        
    with pytest.raises(CircularDependencyError) as exc_info:
        graph.check_cycles(get_deps)
        
    assert "Circular dependency detected" in str(exc_info.value)

def test_valid_dependency_graph_no_cycles():
    graph = ThesisDependencyGraph("g1")
    graph.add_edge(ThesisDependencyEdge("T-2", 1.0, "Relies on T-2"))
    graph.add_edge(ThesisDependencyEdge("T-3", 1.0, "Relies on T-3"))
    
    # T-1 -> T-2 -> T-4
    # T-1 -> T-3 -> T-4
    dep_map = {
        "T-1": ["T-2", "T-3"],
        "T-2": ["T-4"],
        "T-3": ["T-4"],
        "T-4": []
    }
    
    def get_deps(tid):
        return dep_map.get(tid, [])
        
    # Should not raise
    graph.check_cycles(get_deps)
