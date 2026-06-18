import pytest
from karsa.market.application.dtos import (
    UniverseRequestDTO, UniverseRebalanceRequestDTO, UniverseMembershipChangeRequestDTO,
    MarketBreadthRequestDTO, SectorRotationRequestDTO, ForeignFlowAnomalyRequestDTO
)
from karsa.market.application.services import UniverseService, MarketStructureService
from karsa.market.domain.models import UniverseRegistry, MarketStructureSnapshot

class DummyUoW:
    def __enter__(self): pass
    def __exit__(self, *args): pass
    def commit(self): pass
    def rollback(self): pass

class DummyRepo:
    def __init__(self):
        self.items = {}
    def add(self, agg):
        self.items[getattr(agg, "universe_id", getattr(agg, "snapshot_id", None))] = agg
    def get(self, _id):
        return self.items.get(_id)
    def save(self, agg):
        pass
    def list_all(self):
        return list(self.items.values())

def test_universe_service():
    repo = DummyRepo()
    uow = DummyUoW()
    svc = UniverseService(repo, uow)
    
    req = UniverseRequestDTO("u1", "U1", "Desc")
    res = svc.create_universe(req)
    assert res.universe_id == "u1"
    
    req2 = UniverseRebalanceRequestDTO("u1", ["A", "B"])
    res2 = svc.rebalance_universe(req2)
    assert len(res2.members) == 2
    
    req3 = UniverseMembershipChangeRequestDTO("u1", ["C"], ["B"])
    res3 = svc.change_membership(req3)
    assert "C" in res3.members
    assert "B" not in res3.members
    
    assert svc.get_universe("u1") is not None
    assert len(svc.list_universes()) == 1
    
    # Not found cases
    assert svc.rebalance_universe(UniverseRebalanceRequestDTO("fake", [])) is None
    assert svc.change_membership(UniverseMembershipChangeRequestDTO("fake", [], [])) is None

def test_market_service():
    repo = DummyRepo()
    uow = DummyUoW()
    svc = MarketStructureService(repo, uow)
    
    req1 = MarketBreadthRequestDTO("s1", 10, 5, 2, 1)
    res1 = svc.record_breadth(req1)
    assert res1.advancers == 10
    
    req2 = SectorRotationRequestDTO("s1", {"T": 1.0})
    res2 = svc.record_sector_rotation(req2)
    assert res2.sector_strength["T"] == 1.0
    
    req3 = ForeignFlowAnomalyRequestDTO("s1", "A", 1.0, 0.0)
    res3 = svc.record_foreign_flow_anomaly(req3)
    assert len(res3.foreign_flow_anomalies) == 1
    
    assert svc.get_snapshot("s1") is not None
