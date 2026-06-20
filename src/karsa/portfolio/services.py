import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any
from karsa.portfolio.models import PortfolioAggregate, PositionAggregate, CashLedgerAggregate, ValuationAggregate
from karsa.portfolio.value_objects import PositionStatus, AssetExposure
from karsa.portfolio.repositories import PositionRepository, CashLedgerRepository, ValuationRepository
from karsa.portfolio.events import (
    HoldingsUpdatedEvent, CashUpdatedEvent, PositionOpenedEvent, PositionClosedEvent,
    PortfolioValuationCalculatedEvent, ExposureCalculatedEvent
)

class BenchmarkRegistryService:
    def __init__(self):
        self._benchmarks: Dict[str, Decimal] = {}

    def register_benchmark(self, benchmark_id: str, value: Decimal) -> None:
        self._benchmarks[benchmark_id] = value

    def get_benchmark_value(self, benchmark_id: str) -> Optional[Decimal]:
        return self._benchmarks.get(benchmark_id)


class ExposureCalculationService:
    def __init__(self):
        pass

    def calculate_exposures(self, asset_valuations: Dict[str, Decimal], net_asset_value: Decimal) -> List[AssetExposure]:
        exposures = []
        if net_asset_value <= 0:
            for asset_id, val in asset_valuations.items():
                exposures.append(AssetExposure(asset_id, Decimal("0.0"), val))
            return exposures

        for asset_id, val in asset_valuations.items():
            pct = val / net_asset_value
            exposures.append(AssetExposure(asset_id, pct, val))
        return exposures


class PortfolioValuationService:
    def __init__(self, valuation_repo: ValuationRepository, exposure_service: ExposureCalculationService, benchmark_service: BenchmarkRegistryService, events_list: Optional[List[Any]] = None):
        self.valuation_repo = valuation_repo
        self.exposure_service = exposure_service
        self.benchmark_service = benchmark_service
        self.events_list = events_list if events_list is not None else []

    def calculate_and_publish_valuation(self, portfolio_id: str, cash_balance: Decimal, positions: List[PositionAggregate], asset_prices: Dict[str, Decimal], benchmark_ids: List[str], correlation_id: str, causation_id: str) -> ValuationAggregate:
        asset_valuations = {}
        total_asset_value = Decimal("0.0")
        for pos in positions:
            price = asset_prices.get(pos.asset_id, pos.average_cost)
            val = pos.units * price
            asset_valuations[pos.asset_id] = val
            total_asset_value += val

        net_asset_value = total_asset_value + cash_balance

        exposures = self.exposure_service.calculate_exposures(asset_valuations, net_asset_value)

        benchmark_values = {}
        for b_id in benchmark_ids:
            val = self.benchmark_service.get_benchmark_value(b_id)
            if val is not None:
                benchmark_values[b_id] = val

        valuation = ValuationAggregate(
            valuation_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            net_asset_value=net_asset_value,
            cash_balance=cash_balance,
            asset_valuations=asset_valuations,
            exposures=exposures,
            benchmark_values=benchmark_values,
            calculated_at=datetime.utcnow()
        )
        self.valuation_repo.save(valuation)

        from dataclasses import asdict
        self.events_list.append(PortfolioValuationCalculatedEvent(
            event_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            net_asset_value=str(net_asset_value),
            cash_balance=str(cash_balance),
            asset_valuations={k: str(v) for k, v in asset_valuations.items()},
            exposures=[asdict(e) for e in exposures],
            benchmark_values={k: str(v) for k, v in benchmark_values.items()},
            calculated_at=valuation.calculated_at,
            correlation_id=correlation_id,
            causation_id=causation_id
        ))

        self.events_list.append(ExposureCalculatedEvent(
            event_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            exposures=[asdict(e) for e in exposures],
            timestamp=valuation.calculated_at,
            correlation_id=correlation_id,
            causation_id=causation_id
        ))

        return valuation


class PortfolioProjectionService:
    def __init__(self, position_repo: PositionRepository, cash_repo: CashLedgerRepository, valuation_service: PortfolioValuationService, events_list: Optional[List[Any]] = None):
        self.position_repo = position_repo
        self.cash_repo = cash_repo
        self.valuation_service = valuation_service
        self.events_list = events_list if events_list is not None else []

    def consume_order_filled(self, payload: dict, asset_prices: Optional[Dict[str, Decimal]] = None) -> ValuationAggregate:
        portfolio_id = payload["portfolio_id"]
        asset_id = payload.get("asset_id", payload.get("symbol"))
        units_delta = Decimal(payload.get("units", payload.get("quantity", 0)))
        price = Decimal(payload["price"])
        timestamp = datetime.fromisoformat(payload["timestamp"]) if isinstance(payload["timestamp"], str) else payload["timestamp"]
        correlation_id = payload.get("correlation_id", portfolio_id)
        causation_id = payload.get("event_id", portfolio_id)

        pos = self.position_repo.find_by_portfolio_and_asset(portfolio_id, asset_id)
        is_new_position = pos is None
        if not pos:
            pos = PositionAggregate(
                position_id=str(uuid.uuid4()),
                portfolio_id=portfolio_id,
                asset_id=asset_id,
                units=Decimal("0.0"),
                average_cost=Decimal("0.0"),
                status=PositionStatus.OPENING
            )
        
        realized_pnl = Decimal("0.0")
        if units_delta < 0 and pos.units > 0:
            realized_pnl = (price - pos.average_cost) * abs(units_delta)

        pos.update_position(units_delta, price, payload.get("fill_id", str(uuid.uuid4())), timestamp)
        self.position_repo.save(pos)

        self.events_list.append(HoldingsUpdatedEvent(
            event_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            units_delta=str(units_delta),
            total_units=str(pos.units),
            average_cost=str(pos.average_cost),
            timestamp=timestamp,
            correlation_id=correlation_id,
            causation_id=causation_id
        ))

        if is_new_position:
            self.events_list.append(PositionOpenedEvent(
                event_id=str(uuid.uuid4()),
                portfolio_id=portfolio_id,
                position_id=pos.position_id,
                asset_id=asset_id,
                initial_units=str(units_delta),
                entry_price=str(price),
                timestamp=timestamp,
                correlation_id=correlation_id,
                causation_id=causation_id
            ))
        
        if pos.status == PositionStatus.CLOSED:
            self.events_list.append(PositionClosedEvent(
                event_id=str(uuid.uuid4()),
                portfolio_id=portfolio_id,
                position_id=pos.position_id,
                asset_id=asset_id,
                realized_pnl=str(realized_pnl),
                timestamp=timestamp,
                correlation_id=correlation_id,
                causation_id=causation_id
            ))

        if payload.get("order_type") == "DEPOSIT":
            cash_delta = (units_delta * price)
        else:
            cash_delta = -(units_delta * price)
        commission = Decimal(payload.get("commission_bps", "0.0"))
        if commission > 0:
            cash_delta -= abs(units_delta * price) * (commission / Decimal("10000"))

        cash = self.cash_repo.find_by_portfolio(portfolio_id)
        if not cash:
            cash = CashLedgerAggregate(portfolio_id, Decimal("0.0"), Decimal("0.0"))
        
        cash.adjust_cash(cash_delta)
        self.cash_repo.save(cash)

        self.events_list.append(CashUpdatedEvent(
            event_id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            available_balance=str(cash.available_balance),
            held_balance=str(cash.held_balance),
            currency=cash.currency,
            timestamp=timestamp,
            correlation_id=correlation_id,
            causation_id=causation_id
        ))

        active_positions = self.position_repo.list_active_by_portfolio(portfolio_id)
        p_prices = asset_prices if asset_prices is not None else {asset_id: price}
        
        val = self.valuation_service.calculate_and_publish_valuation(
            portfolio_id=portfolio_id,
            cash_balance=cash.available_balance,
            positions=active_positions,
            asset_prices=p_prices,
            benchmark_ids=["SPY"],
            correlation_id=correlation_id,
            causation_id=causation_id
        )

        return val
