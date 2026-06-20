from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from karsa.market.application.dtos import UniverseResponseDTO, MarketStructureSnapshotResponseDTO
from karsa.market.application.services import UniverseService, MarketStructureService

router = APIRouter(prefix="/api/v1/market", tags=["Market Structure"])

# Dependencies would normally inject these, using global mockable vars for simplicity in this structure
universe_service: Optional[UniverseService] = None
market_service: Optional[MarketStructureService] = None

def get_universe_service() -> UniverseService:
    if not universe_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    return universe_service

def get_market_service() -> MarketStructureService:
    if not market_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    return market_service

@router.get("/summary", response_model=MarketStructureSnapshotResponseDTO)
def get_market_summary(snapshot_id: str = "latest", svc: MarketStructureService = Depends(get_market_service)):
    snap = svc.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap

@router.get("/breadth")
def get_market_breadth(snapshot_id: str = "latest", svc: MarketStructureService = Depends(get_market_service)):
    snap = svc.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {
        "advancers": snap.advancers,
        "decliners": snap.decliners,
        "new_highs": snap.new_highs,
        "new_lows": snap.new_lows
    }

@router.get("/foreign-flow")
def get_foreign_flow(snapshot_id: str = "latest", svc: MarketStructureService = Depends(get_market_service)):
    snap = svc.get_snapshot(snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap.foreign_flow_anomalies

@router.get("/universes", response_model=List[UniverseResponseDTO])
def list_universes(svc: UniverseService = Depends(get_universe_service)):
    return svc.list_universes()

@router.get("/universes/{universe_id}", response_model=UniverseResponseDTO)
def get_universe(universe_id: str, svc: UniverseService = Depends(get_universe_service)):
    uni = svc.get_universe(universe_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Universe not found")
    return uni
