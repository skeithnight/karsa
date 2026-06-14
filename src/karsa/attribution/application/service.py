import os
import uuid
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any
from karsa.attribution.domain.model.models import (
    CurrencyAmount,
    CostCalculation,
    AttributionRecord,
    AttributionAdjustment,
    CostLedgerProjection
)
from karsa.attribution.domain.model.repositories import (
    AttributionRecordRepository,
    AttributionAdjustmentRepository
)
from karsa.attribution.events.events import (
    AttributionRecordedEvent,
    AttributionAdjustmentCreatedEvent,
    LedgerProjectionRebuiltEvent
)

class LedgerProjectionService:
    def __init__(self, projection_file_path: Optional[str] = ".karsa/attribution/projection.json"):
        self.projection_file_path = projection_file_path
        self._projection: Dict[str, Dict[str, CostLedgerProjection]] = {}
        if self.projection_file_path:
            self._load()

    def _load(self):
        if not self.projection_file_path or not os.path.exists(self.projection_file_path):
            return
        try:
            with open(self.projection_file_path, "r") as f:
                data = json.load(f)
            self._projection = {}
            for key, vals in data.items():
                self._projection[key] = {}
                for val, proj_data in vals.items():
                    self._projection[key][val] = CostLedgerProjection.from_dict(proj_data)
        except Exception:
            self._projection = {}

    def _save(self):
        if self.projection_file_path:
            os.makedirs(os.path.dirname(self.projection_file_path), exist_ok=True)
            data = {}
            for key, vals in self._projection.items():
                data[key] = {}
                for val, proj in vals.items():
                    data[key][val] = proj.to_dict()
            with open(self.projection_file_path, "w") as f:
                json.dump(data, f, indent=2)

    def build_projection(self, record: AttributionRecord) -> None:
        self.update_dimensions(record.calculated_cost, record)

    def update_dimensions(self, amount: CurrencyAmount, record: AttributionRecord) -> None:
        dims = {
            "research_run_id": record.research_run_id,
            "thesis_id": record.thesis_id,
            "worker_id": record.worker_id,
            "portfolio_id": record.portfolio_id,
            "strategy_id": record.strategy_id
        }
        for k, v in dims.items():
            if v:
                self._add_balance(k, v, amount)
        if record.extended_dimensions:
            for k, v in record.extended_dimensions.items():
                if v:
                    self._add_balance(k, v, amount)
        self._save()

    def _add_balance(self, key: str, value: str, amount: CurrencyAmount) -> None:
        if key not in self._projection:
            self._projection[key] = {}
        if value not in self._projection[key]:
            self._projection[key][value] = CostLedgerProjection(
                dimension_key=key,
                dimension_value=value,
                balance=CurrencyAmount(Decimal("0"), amount.currency),
                updated_at=datetime.utcnow()
            )
        current = self._projection[key][value]
        new_balance = current.balance.add(amount)
        self._projection[key][value] = CostLedgerProjection(
            dimension_key=key,
            dimension_value=value,
            balance=new_balance,
            updated_at=datetime.utcnow()
        )

    def aggregate_balances(self, dimension_key: str, dimension_value: str) -> CurrencyAmount:
        self._load()
        if dimension_key in self._projection and dimension_value in self._projection[dimension_key]:
            return self._projection[dimension_key][dimension_value].balance
        return CurrencyAmount(Decimal("0"), "USD")

    def atomic_projection_swap(self, temp_projection: Dict[str, Dict[str, CostLedgerProjection]]) -> None:
        self._projection = temp_projection
        self._save()

    def clear(self) -> None:
        self._projection = {}
        if self.projection_file_path and os.path.exists(self.projection_file_path):
            try:
                os.remove(self.projection_file_path)
            except Exception:
                pass


class LedgerProjectionRebuildService:
    def __init__(self, record_repo: AttributionRecordRepository, adjustment_repo: AttributionAdjustmentRepository, projection_service: LedgerProjectionService):
        self.record_repo = record_repo
        self.adjustment_repo = adjustment_repo
        self.projection_service = projection_service

    def rebuild_projection(self) -> LedgerProjectionRebuiltEvent:
        records = self.record_repo.list_all()
        adjustments = self.adjustment_repo.list_all()

        temp_projection: Dict[str, Dict[str, CostLedgerProjection]] = {}

        def add_temp_balance(key: str, value: str, amount: CurrencyAmount):
            if key not in temp_projection:
                temp_projection[key] = {}
            if value not in temp_projection[key]:
                temp_projection[key][value] = CostLedgerProjection(
                    dimension_key=key,
                    dimension_value=value,
                    balance=CurrencyAmount(Decimal("0"), amount.currency),
                    updated_at=datetime.utcnow()
                )
            current = temp_projection[key][value]
            temp_projection[key][value] = CostLedgerProjection(
                dimension_key=key,
                dimension_value=value,
                balance=current.balance.add(amount),
                updated_at=datetime.utcnow()
            )

        for r in records:
            adjs = self.adjustment_repo.find_by_original_id(r.attribution_id)
            net_amount = r.calculated_cost
            for adj in adjs:
                net_amount = net_amount.add(adj.adjustment_amount)

            dims = {
                "research_run_id": r.research_run_id,
                "thesis_id": r.thesis_id,
                "worker_id": r.worker_id,
                "portfolio_id": r.portfolio_id,
                "strategy_id": r.strategy_id
            }
            for k, v in dims.items():
                if v:
                    add_temp_balance(k, v, net_amount)
            if r.extended_dimensions:
                for k, v in r.extended_dimensions.items():
                    if v:
                        add_temp_balance(k, v, net_amount)

        self.projection_service.atomic_projection_swap(temp_projection)

        return LedgerProjectionRebuiltEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            record_count=len(records),
            adjustment_count=len(adjustments)
        )


class AttributionService:
    def __init__(
        self,
        record_repo: AttributionRecordRepository,
        adjustment_repo: AttributionAdjustmentRepository,
        projection_service: LedgerProjectionService,
        events_list: Optional[List[Any]] = None
    ):
        self.record_repo = record_repo
        self.adjustment_repo = adjustment_repo
        self.projection_service = projection_service
        self.events_list = events_list if events_list is not None else []

    def validate_idempotency(self, execution_id: str) -> bool:
        record = self.record_repo.find_by_execution_id(execution_id)
        return record is None

    def calculate_cost_from_pricing_snapshot(
        self,
        input_tokens: int,
        output_tokens: int,
        input_rate_per_1m: Decimal,
        output_rate_per_1m: Decimal
    ) -> CurrencyAmount:
        calc = CostCalculation(input_tokens, output_tokens, input_rate_per_1m, output_rate_per_1m)
        return calc.calculate_cost()

    def create_attribution_record(
        self,
        attribution_id: str,
        execution_id: str,
        trace_id: str,
        calculated_cost: CurrencyAmount,
        calculation_details: CostCalculation,
        research_run_id: Optional[str] = None,
        thesis_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        extended_dimensions: Optional[Dict[str, str]] = None
    ) -> AttributionRecord:
        if not self.validate_idempotency(execution_id):
            raise ValueError(f"Duplicate execution_id: {execution_id} already exists")

        record = AttributionRecord(
            attribution_id=attribution_id,
            execution_id=execution_id,
            trace_id=trace_id,
            calculated_cost=calculated_cost,
            calculation_details=calculation_details,
            research_run_id=research_run_id,
            thesis_id=thesis_id,
            worker_id=worker_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            extended_dimensions=extended_dimensions
        )

        self.record_repo.save(record)
        self.projection_service.build_projection(record)

        event = AttributionRecordedEvent(
            event_id=str(uuid.uuid4()),
            attribution_id=attribution_id,
            execution_id=execution_id,
            trace_id=trace_id,
            calculated_cost=calculated_cost.to_dict(),
            research_run_id=research_run_id or "",
            thesis_id=thesis_id or "",
            worker_id=worker_id or "",
            portfolio_id=portfolio_id or "",
            strategy_id=strategy_id or "",
            extended_dimensions=record.extended_dimensions,
            timestamp=datetime.utcnow()
        )
        self.events_list.append(event)

        return record

    def create_adjustment_records(
        self,
        adjustment_id: str,
        original_attribution_id: str,
        adjustment_amount: CurrencyAmount,
        adjustment_reason: str
    ) -> AttributionAdjustment:
        record = self.record_repo.find_by_attribution_id(original_attribution_id)
        if not record:
            raise ValueError(f"Original attribution record not found: {original_attribution_id}")

        adjustment = AttributionAdjustment(
            adjustment_id=adjustment_id,
            original_attribution_id=original_attribution_id,
            adjustment_amount=adjustment_amount,
            adjustment_reason=adjustment_reason
        )

        self.adjustment_repo.save(adjustment)
        self.projection_service.update_dimensions(adjustment_amount, record)

        event = AttributionAdjustmentCreatedEvent(
            event_id=str(uuid.uuid4()),
            adjustment_id=adjustment_id,
            original_attribution_id=original_attribution_id,
            adjustment_amount=adjustment_amount.to_dict(),
            adjustment_reason=adjustment_reason,
            timestamp=datetime.utcnow()
        )
        self.events_list.append(event)

        return adjustment

    def replay_historical_attribution(self, attribution_id: str) -> dict:
        record = self.record_repo.find_by_attribution_id(attribution_id)
        if not record:
            raise ValueError(f"Attribution record not found: {attribution_id}")

        adjustments = self.adjustment_repo.find_by_original_id(attribution_id)
        
        final_cost = record.calculated_cost
        for adj in adjustments:
            final_cost = final_cost.add(adj.adjustment_amount)

        return {
            "attribution_id": record.attribution_id,
            "execution_id": record.execution_id,
            "trace_id": record.trace_id,
            "original_cost": record.calculated_cost.to_dict(),
            "calculation_details": record.calculation_details.to_dict(),
            "adjustments": [adj.to_dict() for adj in adjustments],
            "final_cost": final_cost.to_dict(),
            "dimensions": {
                "research_run_id": record.research_run_id,
                "thesis_id": record.thesis_id,
                "worker_id": record.worker_id,
                "portfolio_id": record.portfolio_id,
                "strategy_id": record.strategy_id,
                "extended_dimensions": record.extended_dimensions
            }
        }

    def query_attribution_records(self, attribution_id: str) -> Optional[AttributionRecord]:
        return self.record_repo.find_by_attribution_id(attribution_id)
