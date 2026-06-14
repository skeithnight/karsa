import pytest
from decimal import Decimal
from karsa.attribution.domain.model.models import CurrencyAmount, CostCalculation
from karsa.attribution.infrastructure.repositories import (
    InMemoryAttributionRecordRepository,
    InMemoryAttributionAdjustmentRepository
)
from karsa.attribution.application.service import (
    LedgerProjectionService,
    LedgerProjectionRebuildService,
    AttributionService
)

def test_attribution_services_flow():
    record_repo = InMemoryAttributionRecordRepository()
    adjustment_repo = InMemoryAttributionAdjustmentRepository()
    projection_service = LedgerProjectionService(projection_file_path=None)
    
    events = []
    service = AttributionService(
        record_repo=record_repo,
        adjustment_repo=adjustment_repo,
        projection_service=projection_service,
        events_list=events
    )

    cost = service.calculate_cost_from_pricing_snapshot(
        input_tokens=1000,
        output_tokens=2000,
        input_rate_per_1m=Decimal("10.00"),
        output_rate_per_1m=Decimal("50.00")
    )
    assert cost.amount == Decimal("0.11")

    details = CostCalculation(1000, 2000, Decimal("10.00"), Decimal("50.00"))
    record = service.create_attribution_record(
        attribution_id="attr-1",
        execution_id="exec-1",
        trace_id="trace-1",
        calculated_cost=cost,
        calculation_details=details,
        portfolio_id="port-A",
        strategy_id="strat-X",
        extended_dimensions={"region": "us-east"}
    )
    assert record.attribution_id == "attr-1"
    assert record_repo.find_by_attribution_id("attr-1") is not None
    assert len(events) == 1
    assert events[0].attribution_id == "attr-1"

    assert service.validate_idempotency("exec-1") is False
    with pytest.raises(ValueError):
        service.create_attribution_record(
            attribution_id="attr-2",
            execution_id="exec-1",
            trace_id="trace-2",
            calculated_cost=cost,
            calculation_details=details
        )

    bal_port = projection_service.aggregate_balances("portfolio_id", "port-A")
    assert bal_port.amount == Decimal("0.11")
    bal_region = projection_service.aggregate_balances("region", "us-east")
    assert bal_region.amount == Decimal("0.11")
    
    adj_cost = CurrencyAmount(Decimal("0.04"), "USD")
    adjustment = service.create_adjustment_records(
        adjustment_id="adj-1",
        original_attribution_id="attr-1",
        adjustment_amount=adj_cost,
        adjustment_reason="pricing_drift"
    )
    assert adjustment.adjustment_id == "adj-1"
    assert len(adjustment_repo.find_by_original_id("attr-1")) == 1
    assert len(events) == 2

    assert projection_service.aggregate_balances("portfolio_id", "port-A").amount == Decimal("0.15")

    replay = service.replay_historical_attribution("attr-1")
    assert replay["attribution_id"] == "attr-1"
    assert replay["original_cost"]["amount"] == "0.11"
    assert replay["final_cost"]["amount"] == "0.15"
    assert len(replay["adjustments"]) == 1

    rebuild_service = LedgerProjectionRebuildService(record_repo, adjustment_repo, projection_service)
    
    projection_service.clear()
    assert projection_service.aggregate_balances("portfolio_id", "port-A").amount == Decimal("0")

    rebuild_event = rebuild_service.rebuild_projection()
    assert rebuild_event.record_count == 1
    assert rebuild_event.adjustment_count == 1
    assert projection_service.aggregate_balances("portfolio_id", "port-A").amount == Decimal("0.15")
