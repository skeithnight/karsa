from typing import Optional, List
from sqlalchemy.orm import Session
from karsa.market.domain.models import UniverseRegistry, MarketStructureSnapshot
from karsa.market.infrastructure.storage.models import (
    MarketUniverseModel, 
    UniverseMemberModel,
    MarketStructureSnapshotModel
)

class UniverseRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, aggregate: UniverseRegistry):
        model = MarketUniverseModel(
            universe_id=aggregate.universe_id,
            name=aggregate.name,
            description=aggregate.description
        )
        for member in aggregate.members:
            model.members.append(UniverseMemberModel(asset_id=member))
        self.session.add(model)

    def get(self, universe_id: str) -> Optional[UniverseRegistry]:
        model = self.session.query(MarketUniverseModel).filter_by(universe_id=universe_id).first()
        if not model:
            return None
        
        agg = UniverseRegistry(
            universe_id=model.universe_id,
            name=model.name,
            description=model.description
        )
        agg.members = {m.asset_id for m in model.members}
        agg._domain_events.clear()
        return agg

    def save(self, aggregate: UniverseRegistry):
        model = self.session.query(MarketUniverseModel).filter_by(universe_id=aggregate.universe_id).first()
        if model:
            model.name = aggregate.name
            model.description = aggregate.description
            
            # Sync members
            existing = {m.asset_id: m for m in model.members}
            target = aggregate.members
            
            # Remove
            for asset_id, m in existing.items():
                if asset_id not in target:
                    self.session.delete(m)
            
            # Add
            for asset_id in target:
                if asset_id not in existing:
                    model.members.append(UniverseMemberModel(asset_id=asset_id))
                    
    def list_all(self) -> List[UniverseRegistry]:
        models = self.session.query(MarketUniverseModel).all()
        result = []
        for model in models:
            agg = UniverseRegistry(
                universe_id=model.universe_id,
                name=model.name,
                description=model.description
            )
            agg.members = {m.asset_id for m in model.members}
            agg._domain_events.clear()
            result.append(agg)
        return result


class MarketStructureRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, aggregate: MarketStructureSnapshot):
        model = MarketStructureSnapshotModel(
            snapshot_id=aggregate.snapshot_id,
            advancers=aggregate.advancers,
            decliners=aggregate.decliners,
            new_highs=aggregate.new_highs,
            new_lows=aggregate.new_lows,
            sector_strength=aggregate.sector_strength,
            foreign_flow_anomalies=aggregate.foreign_flow_anomalies
        )
        self.session.add(model)

    def get(self, snapshot_id: str) -> Optional[MarketStructureSnapshot]:
        model = self.session.query(MarketStructureSnapshotModel).filter_by(snapshot_id=snapshot_id).first()
        if not model:
            return None
            
        agg = MarketStructureSnapshot(snapshot_id=model.snapshot_id)
        agg.advancers = model.advancers
        agg.decliners = model.decliners
        agg.new_highs = model.new_highs
        agg.new_lows = model.new_lows
        agg.sector_strength = model.sector_strength
        agg.foreign_flow_anomalies = model.foreign_flow_anomalies
        agg._domain_events.clear()
        return agg
        
    def save(self, aggregate: MarketStructureSnapshot):
        model = self.session.query(MarketStructureSnapshotModel).filter_by(snapshot_id=aggregate.snapshot_id).first()
        if model:
            model.advancers = aggregate.advancers
            model.decliners = aggregate.decliners
            model.new_highs = aggregate.new_highs
            model.new_lows = aggregate.new_lows
            model.sector_strength = aggregate.sector_strength
            model.foreign_flow_anomalies = aggregate.foreign_flow_anomalies
