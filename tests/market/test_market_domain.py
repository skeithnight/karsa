import pytest
from karsa.market.domain.models import UniverseRegistry, MarketStructureSnapshot

def test_universe_aggregate():
    u = UniverseRegistry("lq45", "LQ45", "Top 45")
    assert u.universe_id == "lq45"
    assert u.aggregate_id == "lq45"
    
    events = u.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_name == "UniverseCreatedEvent"
    assert events[0].aggregate_type == "UniverseRegistry"
    
    u.rebalance(["BBCA", "BBRI"])
    assert len(u.members) == 2
    
    events = u.pull_domain_events()
    assert events[0].event_name == "UniverseRebalancedEvent"
    assert set(events[0].members) == {"BBCA", "BBRI"}
    
    u.change_membership(added=["TLKM"], removed=["BBRI"])
    assert "TLKM" in u.members
    assert "BBRI" not in u.members
    assert "BBCA" in u.members
    
    events = u.pull_domain_events()
    assert events[0].event_name == "UniverseMembershipChangedEvent"
    assert "TLKM" in events[0].added_assets
    assert "BBRI" in events[0].removed_assets

def test_market_snapshot_aggregate():
    s = MarketStructureSnapshot("snap-1")
    assert s.snapshot_id == "snap-1"
    
    s.record_market_breadth(100, 50, 10, 5)
    assert s.advancers == 100
    events = s.pull_domain_events()
    assert events[0].event_name == "MarketBreadthCalculatedEvent"
    assert events[0].advancers == 100
    
    s.record_sector_rotation({"FINANCE": 0.8, "TECH": -0.2})
    assert s.sector_strength["FINANCE"] == 0.8
    events = s.pull_domain_events()
    assert events[0].event_name == "SectorRotationDetectedEvent"
    
    s.record_foreign_flow_anomaly("BBCA", 0.9, 0.1)
    assert len(s.foreign_flow_anomalies) == 1
    events = s.pull_domain_events()
    assert events[0].event_name == "ForeignFlowAnomalyDetectedEvent"
    assert events[0].accumulation_score == 0.9
