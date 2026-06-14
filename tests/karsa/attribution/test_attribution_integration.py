import os
import shutil
import pytest
from decimal import Decimal
from karsa.attribution.domain.model.models import CurrencyAmount, CostCalculation
from karsa.attribution.infrastructure.repositories import (
    FileAttributionRecordRepository,
    FileAttributionAdjustmentRepository
)
from karsa.attribution.application.service import (
    LedgerProjectionService,
    LedgerProjectionRebuildService,
    AttributionService
)

def test_attribution_integration_flow():
    test_record_dir = ".karsa/test_integration/records/"
    test_adj_dir = ".karsa/test_integration/adjustments/"
    test_proj_path = ".karsa/test_integration/projection.json"

    if os.path.exists(".karsa/test_integration/"):
        shutil.rmtree(".karsa/test_integration/")

    record_repo = FileAttributionRecordRepository(storage_dir=test_record_dir)
    adjustment_repo = FileAttributionAdjustmentRepository(storage_dir=test_adj_dir)
    projection_service = LedgerProjectionService(projection_file_path=test_proj_path)

    events = []
    service = AttributionService(
        record_repo=record_repo,
        adjustment_repo=adjustment_repo,
        projection_service=projection_service,
        events_list=events
    )

    cost1 = service.calculate_cost_from_pricing_snapshot(
        input_tokens=1000,
        output_tokens=3000,
        input_rate_per_1m=Decimal("15.00"),
        output_rate_per_1m=Decimal("60.00")
    )
    assert cost1.amount == Decimal("0.195")

    record1 = service.create_attribution_record(
        attribution_id="attr-int-1",
        execution_id="exec-int-1",
        trace_id="trace-int-1",
        calculated_cost=cost1,
        calculation_details=CostCalculation(1000, 3000, Decimal("15.00"), Decimal("60.00")),
        research_run_id="run-int-A",
        portfolio_id="port-int-A",
        extended_dimensions={"tenant": "acme"}
    )

    assert projection_service.aggregate_balances("portfolio_id", "port-int-A").amount == Decimal("0.195")
    assert projection_service.aggregate_balances("tenant", "acme").amount == Decimal("0.195")

    adj_amount = CurrencyAmount(Decimal("0.05"), "USD")
    service.create_adjustment_records(
        adjustment_id="adj-int-1",
        original_attribution_id="attr-int-1",
        adjustment_amount=adj_amount,
        adjustment_reason="pricing_drift"
    )

    assert projection_service.aggregate_balances("portfolio_id", "port-int-A").amount == Decimal("0.245")

    replay_res = service.replay_historical_attribution("attr-int-1")
    assert replay_res["original_cost"]["amount"] == "0.195"
    assert replay_res["final_cost"]["amount"] == "0.245"
    assert len(replay_res["adjustments"]) == 1

    projection_service.clear()
    assert projection_service.aggregate_balances("portfolio_id", "port-int-A").amount == Decimal("0")

    rebuild_service = LedgerProjectionRebuildService(record_repo, adjustment_repo, projection_service)
    rebuild_event = rebuild_service.rebuild_projection()
    
    assert rebuild_event.record_count == 1
    assert rebuild_event.adjustment_count == 1
    assert projection_service.aggregate_balances("portfolio_id", "port-int-A").amount == Decimal("0.245")

    if os.path.exists(".karsa/test_integration/"):
        shutil.rmtree(".karsa/test_integration/")

def test_replay_after_pricing_change():
    test_record_dir = ".karsa/test_pricing_change/records/"
    test_adj_dir = ".karsa/test_pricing_change/adjustments/"
    test_proj_path = ".karsa/test_pricing_change/projection.json"

    if os.path.exists(".karsa/test_pricing_change/"):
        shutil.rmtree(".karsa/test_pricing_change/")

    record_repo = FileAttributionRecordRepository(storage_dir=test_record_dir)
    adjustment_repo = FileAttributionAdjustmentRepository(storage_dir=test_adj_dir)
    projection_service = LedgerProjectionService(projection_file_path=test_proj_path)

    events = []
    service = AttributionService(
        record_repo=record_repo,
        adjustment_repo=adjustment_repo,
        projection_service=projection_service,
        events_list=events
    )

    # Initial pricing rate: input_rate=15.00, output_rate=60.00
    cost = service.calculate_cost_from_pricing_snapshot(
        input_tokens=1000,
        output_tokens=3000,
        input_rate_per_1m=Decimal("15.00"),
        output_rate_per_1m=Decimal("60.00")
    )
    assert cost.amount == Decimal("0.195")

    record = service.create_attribution_record(
        attribution_id="attr-pricing-1",
        execution_id="exec-pricing-1",
        trace_id="trace-pricing-1",
        calculated_cost=cost,
        calculation_details=CostCalculation(1000, 3000, Decimal("15.00"), Decimal("60.00")),
        research_run_id="run-pricing"
    )

    # Now, simulate a pricing change in the provider registry (e.g. rate changes to input_rate=30.00, output_rate=120.00)
    # Replay must NOT query the active provider pricing, but load the stored pricing snapshot
    replay_before = service.replay_historical_attribution("attr-pricing-1")
    assert Decimal(replay_before["original_cost"]["amount"]) == Decimal("0.195")

    # If we recalculate today with the new pricing, it would be different, but replay uses the original record.
    new_cost = service.calculate_cost_from_pricing_snapshot(
        input_tokens=1000,
        output_tokens=3000,
        input_rate_per_1m=Decimal("30.00"),
        output_rate_per_1m=Decimal("120.00")
    )
    assert new_cost.amount == Decimal("0.390")  # Cost doubled under new rates

    # Replay after the simulated pricing change still yields the original cost
    replay_after = service.replay_historical_attribution("attr-pricing-1")
    assert Decimal(replay_after["original_cost"]["amount"]) == Decimal("0.195")
    assert replay_after["original_cost"]["amount"] == replay_before["original_cost"]["amount"]

    if os.path.exists(".karsa/test_pricing_change/"):
        shutil.rmtree(".karsa/test_pricing_change/")

