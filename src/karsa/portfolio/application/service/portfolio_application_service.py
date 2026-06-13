import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from karsa.portfolio.domain.model.portfolio import Portfolio, CashTarget
from karsa.portfolio.domain.repository.portfolio_repository import PortfolioRepository
from karsa.portfolio.domain.service.rebalancing_engine import RebalancingEngine
from karsa.portfolio.application.port.treasury_port import TreasuryPort
from karsa.portfolio.application.port.regime_port import RegimePort
from karsa.portfolio.application.port.allocation_port import AllocationPort
from karsa.shared.infrastructure.uow import UnitOfWork
from karsa.shared.infrastructure.outbox import OutboxRecord
from karsa.shared.events.envelope import PlatformEventEnvelope
from karsa.shared.events.portfolio import PortfolioDecisionProposed, PortfolioTargetUpdated
from karsa.shared.domain.snapshot import DecisionContextSnapshot
from karsa.shared.domain.identity import OriginatorIdentity

class PortfolioApplicationService:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        treasury_port: TreasuryPort,
        regime_port: RegimePort,
        allocation_port: AllocationPort,
        rebalancing_engine: RebalancingEngine,
        uow: UnitOfWork
    ):
        self.portfolio_repo = portfolio_repo
        self.treasury_port = treasury_port
        self.regime_port = regime_port
        self.allocation_port = allocation_port
        self.rebalancing_engine = rebalancing_engine
        self.uow = uow

    def propose_rebalance(self, portfolio_id: str, target_cash_percentage: float = 0.10) -> None:
        with self.uow:
            portfolio = self.portfolio_repo.get_by_id(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            allocations = self.allocation_port.get_allocations_for_portfolio(portfolio_id)
            mappings = self.allocation_port.get_mappings_for_portfolio(portfolio_id)
            
            if not allocations:
                raise ValueError(f"No active allocations found for portfolio {portfolio_id}")

            buying_power = self.treasury_port.get_buying_power(portfolio_id)
            regime = self.regime_port.get_current_regime()
            cash_target = CashTarget(target_cash_percentage)

            result = self.rebalancing_engine.rebalance(
                portfolio=portfolio,
                allocations=allocations,
                mappings=mappings,
                cash_target=cash_target,
                buying_power=buying_power,
                regime=regime
            )

            # Generate DecisionContextSnapshot
            snapshot = DecisionContextSnapshot(
                decision_context_id=str(uuid.uuid4()),
                trigger_event_id=str(uuid.uuid4()),
                trigger_event_type="ManualTrigger",
                constraint_fingerprint="fp123",
                optimizer_version="v1.0",
                engine_version="v1.0",
                git_hash="unknown",
                created_at=datetime.utcnow().isoformat(),
                dependency_snapshot_ids={}
            )

            # Draft PortfolioDecisionProposed event
            originator = OriginatorIdentity("SYSTEM", "SYSTEM", "1.0")
            event_payload = PortfolioDecisionProposed(
                decision_payload={"decision_id": result.decision.decision_id, "target_snapshot_id": result.target_snapshot.snapshot_id},
                context_snapshot=snapshot.__dict__,
                originator_identity=originator.__dict__
            )

            envelope = PlatformEventEnvelope(
                event_id=str(uuid.uuid4()),
                event_type="PortfolioDecisionProposed",
                correlation_id=str(uuid.uuid4()),
                causation_id=str(uuid.uuid4()),
                aggregate_type="Portfolio",
                aggregate_id=portfolio.portfolio_id,
                aggregate_version=portfolio.aggregate_version,
                occurred_at=datetime.utcnow().isoformat(),
                schema_version="1.0",
                payload=event_payload.__dict__
            )

            # NOTE: We do NOT persist portfolio here. Only the OutboxRecord.
            # We assume UoW has access to outbox
            if hasattr(self.uow, 'outbox_repository'):
                self.uow.outbox_repository.save(OutboxRecord(envelope.event_id, envelope.serialize()))

    def apply_approved_decision(self, portfolio_id: str, target_snapshot_id: str, correlation_id: str, causation_id: str) -> None:
        with self.uow:
            portfolio = self.portfolio_repo.get_by_id(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            portfolio.current_target_snapshot_id = target_snapshot_id
            portfolio.increment_version()
            self.portfolio_repo.save(portfolio)

            event_payload = PortfolioTargetUpdated(
                portfolio_id=portfolio.portfolio_id,
                target_snapshot_id=target_snapshot_id
            )

            envelope = PlatformEventEnvelope(
                event_id=str(uuid.uuid4()),
                event_type="PortfolioTargetUpdated",
                correlation_id=correlation_id,
                causation_id=causation_id,
                aggregate_type="Portfolio",
                aggregate_id=portfolio.portfolio_id,
                aggregate_version=portfolio.aggregate_version,
                occurred_at=datetime.utcnow().isoformat(),
                schema_version="1.0",
                payload=event_payload.__dict__
            )

            if hasattr(self.uow, 'outbox_repository'):
                self.uow.outbox_repository.save(OutboxRecord(envelope.event_id, envelope.serialize()))
