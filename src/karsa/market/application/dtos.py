from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class UniverseRequestDTO:
    universe_id: str
    name: str
    description: str

@dataclass
class UniverseRebalanceRequestDTO:
    universe_id: str
    members: List[str]

@dataclass
class UniverseMembershipChangeRequestDTO:
    universe_id: str
    added_assets: List[str]
    removed_assets: List[str]

@dataclass
class MarketBreadthRequestDTO:
    snapshot_id: str
    advancers: int
    decliners: int
    new_highs: int
    new_lows: int

@dataclass
class SectorRotationRequestDTO:
    snapshot_id: str
    sector_strength: Dict[str, float]

@dataclass
class ForeignFlowAnomalyRequestDTO:
    snapshot_id: str
    asset_id: str
    accumulation_score: float
    distribution_score: float

@dataclass
class UniverseResponseDTO:
    universe_id: str
    name: str
    description: str
    members: List[str]

@dataclass
class MarketStructureSnapshotResponseDTO:
    snapshot_id: str
    advancers: int
    decliners: int
    new_highs: int
    new_lows: int
    sector_strength: Dict[str, float]
    foreign_flow_anomalies: List[Dict[str, Any]]
