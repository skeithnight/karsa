from typing import Optional, List
from karsa.market.domain.models import UniverseRegistry, MarketStructureSnapshot
from karsa.market.application.dtos import (
    UniverseRequestDTO,
    UniverseRebalanceRequestDTO,
    UniverseMembershipChangeRequestDTO,
    UniverseResponseDTO,
    MarketBreadthRequestDTO,
    SectorRotationRequestDTO,
    ForeignFlowAnomalyRequestDTO,
    MarketStructureSnapshotResponseDTO
)

class UniverseService:
    def __init__(self, repository, uow):
        self.repository = repository
        self.uow = uow

    def _to_dto(self, agg: UniverseRegistry) -> UniverseResponseDTO:
        return UniverseResponseDTO(
            universe_id=agg.universe_id,
            name=agg.name,
            description=agg.description,
            members=list(agg.members)
        )

    def create_universe(self, req: UniverseRequestDTO) -> UniverseResponseDTO:
        agg = UniverseRegistry(
            universe_id=req.universe_id,
            name=req.name,
            description=req.description
        )
        with self.uow:
            self.repository.add(agg)
            self.uow.commit()
        return self._to_dto(agg)

    def rebalance_universe(self, req: UniverseRebalanceRequestDTO) -> Optional[UniverseResponseDTO]:
        with self.uow:
            agg = self.repository.get(req.universe_id)
            if not agg:
                return None
            agg.rebalance(req.members)
            self.repository.save(agg)
            self.uow.commit()
        return self._to_dto(agg)

    def change_membership(self, req: UniverseMembershipChangeRequestDTO) -> Optional[UniverseResponseDTO]:
        with self.uow:
            agg = self.repository.get(req.universe_id)
            if not agg:
                return None
            agg.change_membership(req.added_assets, req.removed_assets)
            self.repository.save(agg)
            self.uow.commit()
        return self._to_dto(agg)
        
    def get_universe(self, universe_id: str) -> Optional[UniverseResponseDTO]:
        agg = self.repository.get(universe_id)
        return self._to_dto(agg) if agg else None

    def list_universes(self) -> List[UniverseResponseDTO]:
        aggs = self.repository.list_all()
        return [self._to_dto(agg) for agg in aggs]

class MarketStructureService:
    def __init__(self, repository, uow):
        self.repository = repository
        self.uow = uow
        
    def _to_dto(self, agg: MarketStructureSnapshot) -> MarketStructureSnapshotResponseDTO:
        return MarketStructureSnapshotResponseDTO(
            snapshot_id=agg.snapshot_id,
            advancers=agg.advancers,
            decliners=agg.decliners,
            new_highs=agg.new_highs,
            new_lows=agg.new_lows,
            sector_strength=agg.sector_strength,
            foreign_flow_anomalies=agg.foreign_flow_anomalies
        )
        
    def _get_or_create(self, snapshot_id: str) -> MarketStructureSnapshot:
        agg = self.repository.get(snapshot_id)
        if not agg:
            agg = MarketStructureSnapshot(snapshot_id=snapshot_id)
            self.repository.add(agg)
        return agg

    def record_breadth(self, req: MarketBreadthRequestDTO) -> MarketStructureSnapshotResponseDTO:
        with self.uow:
            agg = self._get_or_create(req.snapshot_id)
            agg.record_market_breadth(req.advancers, req.decliners, req.new_highs, req.new_lows)
            self.repository.save(agg)
            self.uow.commit()
        return self._to_dto(agg)

    def record_sector_rotation(self, req: SectorRotationRequestDTO) -> MarketStructureSnapshotResponseDTO:
        with self.uow:
            agg = self._get_or_create(req.snapshot_id)
            agg.record_sector_rotation(req.sector_strength)
            self.repository.save(agg)
            self.uow.commit()
        return self._to_dto(agg)
        
    def record_foreign_flow_anomaly(self, req: ForeignFlowAnomalyRequestDTO) -> MarketStructureSnapshotResponseDTO:
        with self.uow:
            agg = self._get_or_create(req.snapshot_id)
            agg.record_foreign_flow_anomaly(req.asset_id, req.accumulation_score, req.distribution_score)
            self.repository.save(agg)
            self.uow.commit()
        return self._to_dto(agg)

    def get_snapshot(self, snapshot_id: str) -> Optional[MarketStructureSnapshotResponseDTO]:
        agg = self.repository.get(snapshot_id)
        return self._to_dto(agg) if agg else None
