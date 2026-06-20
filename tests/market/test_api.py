import pytest
from fastapi.testclient import TestClient
from karsa.market.presentation.api import router, get_universe_service, get_market_service
from karsa.market.application.dtos import MarketStructureSnapshotResponseDTO, UniverseResponseDTO
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

class MockMarketSvc:
    def get_snapshot(self, sid):
        if sid == "latest":
            return MarketStructureSnapshotResponseDTO(
                snapshot_id="latest",
                advancers=10, decliners=5, new_highs=2, new_lows=1,
                sector_strength={"T": 1.0},
                foreign_flow_anomalies=[{"asset_id": "A"}]
            )
        return None

class MockUniverseSvc:
    def get_universe(self, uid):
        if uid == "u1":
            return UniverseResponseDTO("u1", "U", "D", ["A"])
        return None
    def list_universes(self):
        return [UniverseResponseDTO("u1", "U", "D", ["A"])]

app.dependency_overrides[get_market_service] = MockMarketSvc
app.dependency_overrides[get_universe_service] = MockUniverseSvc

client = TestClient(app)

def test_api_market_summary():
    r = client.get("/api/v1/market/summary")
    assert r.status_code == 200
    assert r.json()["advancers"] == 10
    
    r = client.get("/api/v1/market/summary?snapshot_id=fake")
    assert r.status_code == 404

def test_api_market_breadth():
    r = client.get("/api/v1/market/breadth")
    assert r.status_code == 200
    assert r.json()["advancers"] == 10
    
    r = client.get("/api/v1/market/breadth?snapshot_id=fake")
    assert r.status_code == 404

def test_api_foreign_flow():
    r = client.get("/api/v1/market/foreign-flow")
    assert r.status_code == 200
    assert len(r.json()) == 1
    
    r = client.get("/api/v1/market/foreign-flow?snapshot_id=fake")
    assert r.status_code == 404

def test_api_list_universes():
    r = client.get("/api/v1/market/universes")
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_api_get_universe():
    r = client.get("/api/v1/market/universes/u1")
    assert r.status_code == 200
    assert r.json()["universe_id"] == "u1"
    
    r = client.get("/api/v1/market/universes/fake")
    assert r.status_code == 404
