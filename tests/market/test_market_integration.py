import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from karsa.shared.persistence.base import Base
from karsa.market.domain.models import UniverseRegistry, MarketStructureSnapshot
from karsa.market.infrastructure.storage.repositories import UniverseRepository, MarketStructureRepository
from karsa.market.infrastructure.storage.models import MarketUniverseModel

engine = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=engine)

def setup_module(module):
    Base.metadata.create_all(engine)

def teardown_module(module):
    Base.metadata.drop_all(engine)

def test_universe_repository():
    session = Session()
    repo = UniverseRepository(session)
    
    agg = UniverseRegistry("u-1", "U1", "Desc")
    agg.rebalance(["A", "B"])
    repo.add(agg)
    session.commit()
    
    fetched = repo.get("u-1")
    assert fetched is not None
    assert fetched.name == "U1"
    assert "A" in fetched.members
    
    fetched.change_membership(["C"], ["A"])
    repo.save(fetched)
    session.commit()
    
    fetched2 = repo.get("u-1")
    assert "C" in fetched2.members
    assert "A" not in fetched2.members
    
    all_uni = repo.list_all()
    assert len(all_uni) == 1
    assert repo.get("fake") is None

def test_market_repository():
    session = Session()
    repo = MarketStructureRepository(session)
    
    agg = MarketStructureSnapshot("snap-2")
    agg.record_market_breadth(10, 5, 2, 1)
    agg.record_sector_rotation({"TECH": 1.0})
    agg.record_foreign_flow_anomaly("BBCA", 1.0, 0.0)
    
    repo.add(agg)
    session.commit()
    
    fetched = repo.get("snap-2")
    assert fetched is not None
    assert fetched.advancers == 10
    assert fetched.sector_strength["TECH"] == 1.0
    assert fetched.foreign_flow_anomalies[0]["asset_id"] == "BBCA"
    
    fetched.record_market_breadth(20, 10, 5, 2)
    repo.save(fetched)
    session.commit()
    
    fetched2 = repo.get("snap-2")
    assert fetched2.advancers == 20
    assert repo.get("fake") is None
