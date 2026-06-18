from typing import Dict, Any, List, Set
from datetime import datetime
import uuid
from karsa.shared.domain.aggregate import AggregateRoot
from karsa.market.events.events import (
    UniverseCreatedEvent,
    UniverseMembershipChangedEvent,
    UniverseRebalancedEvent,
    MarketBreadthCalculatedEvent,
    SectorRotationDetectedEvent,
    ForeignFlowAnomalyDetectedEvent
)

class UniverseRegistry(AggregateRoot):
    def __init__(self, universe_id: str, name: str, description: str):
        super().__init__()
        self.universe_id = universe_id
        self.aggregate_id = universe_id
        self.name = name
        self.description = description
        self.members: Set[str] = set()
        self.updated_at = datetime.utcnow()
        
        self.record_event(UniverseCreatedEvent(
            universe_id=self.universe_id,
            name=self.name,
            description=self.description
        ))

    def rebalance(self, new_members: List[str]):
        self.members = set(new_members)
        self.updated_at = datetime.utcnow()
        self.record_event(UniverseRebalancedEvent(
            universe_id=self.universe_id,
            members=list(self.members)
        ))

    def change_membership(self, added: List[str], removed: List[str]):
        added_set = set(added)
        removed_set = set(removed)
        
        # Calculate actual changes to avoid dummy events
        actual_added = added_set - self.members
        actual_removed = removed_set.intersection(self.members)
        
        if not actual_added and not actual_removed:
            return
            
        self.members.update(actual_added)
        self.members.difference_update(actual_removed)
        self.updated_at = datetime.utcnow()
        
        self.record_event(UniverseMembershipChangedEvent(
            universe_id=self.universe_id,
            added_assets=list(actual_added),
            removed_assets=list(actual_removed)
        ))

class MarketStructureSnapshot(AggregateRoot):
    def __init__(self, snapshot_id: str):
        super().__init__()
        self.snapshot_id = snapshot_id
        self.aggregate_id = snapshot_id
        self.created_at = datetime.utcnow()
        
        # State
        self.advancers = 0
        self.decliners = 0
        self.new_highs = 0
        self.new_lows = 0
        self.sector_strength: Dict[str, float] = {}
        self.foreign_flow_anomalies: List[Dict[str, Any]] = []

    def record_market_breadth(self, advancers: int, decliners: int, new_highs: int, new_lows: int):
        self.advancers = advancers
        self.decliners = decliners
        self.new_highs = new_highs
        self.new_lows = new_lows
        
        self.record_event(MarketBreadthCalculatedEvent(
            snapshot_id=self.snapshot_id,
            advancers=self.advancers,
            decliners=self.decliners,
            new_highs=self.new_highs,
            new_lows=self.new_lows
        ))

    def record_sector_rotation(self, sector_strength: Dict[str, float]):
        self.sector_strength = sector_strength
        self.record_event(SectorRotationDetectedEvent(
            snapshot_id=self.snapshot_id,
            sector_strength=self.sector_strength
        ))

    def record_foreign_flow_anomaly(self, asset_id: str, accumulation: float, distribution: float):
        anomaly = {
            "asset_id": asset_id,
            "accumulation_score": accumulation,
            "distribution_score": distribution
        }
        self.foreign_flow_anomalies.append(anomaly)
        
        self.record_event(ForeignFlowAnomalyDetectedEvent(
            snapshot_id=self.snapshot_id,
            asset_id=asset_id,
            accumulation_score=accumulation,
            distribution_score=distribution
        ))
