from dataclasses import dataclass
from typing import Dict, Any, List
from karsa.shared.domain.event import DomainEvent

@dataclass
class UniverseCreatedEvent(DomainEvent):
    universe_id: str = ""
    name: str = ""
    description: str = ""

@dataclass
class UniverseMembershipChangedEvent(DomainEvent):
    universe_id: str = ""
    added_assets: List[str] = None
    removed_assets: List[str] = None
    
    def __post_init__(self):
        if self.added_assets is None:
            self.added_assets = []
        if self.removed_assets is None:
            self.removed_assets = []

@dataclass
class UniverseRebalancedEvent(DomainEvent):
    universe_id: str = ""
    members: List[str] = None
    
    def __post_init__(self):
        if self.members is None:
            self.members = []

@dataclass
class MarketBreadthCalculatedEvent(DomainEvent):
    snapshot_id: str = ""
    advancers: int = 0
    decliners: int = 0
    new_highs: int = 0
    new_lows: int = 0

@dataclass
class SectorRotationDetectedEvent(DomainEvent):
    snapshot_id: str = ""
    sector_strength: Dict[str, float] = None
    
    def __post_init__(self):
        if self.sector_strength is None:
            self.sector_strength = {}

@dataclass
class ForeignFlowAnomalyDetectedEvent(DomainEvent):
    snapshot_id: str = ""
    asset_id: str = ""
    accumulation_score: float = 0.0
    distribution_score: float = 0.0
