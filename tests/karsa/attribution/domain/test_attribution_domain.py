import pytest
from datetime import datetime
from decimal import Decimal
from karsa.attribution.domain.model.models import (
    CurrencyAmount,
    CostCalculation,
    AttributionRecord,
    AttributionAdjustment
)

def test_currency_amount():
    c1 = CurrencyAmount(Decimal("10.50"), "USD")
    c2 = CurrencyAmount(Decimal("5.25"), "USD")
    c3 = c1.add(c2)
    assert c3.amount == Decimal("15.75")
    assert c3.currency == "USD"

    with pytest.raises(ValueError):
        c1.add(CurrencyAmount(Decimal("1"), "EUR"))

def test_cost_calculation():
    calc = CostCalculation(
        input_tokens=1000,
        output_tokens=2000,
        input_rate_per_1m=Decimal("15.00"),
        output_rate_per_1m=Decimal("60.00")
    )
    cost = calc.calculate_cost()
    assert cost.amount == Decimal("0.135")
    assert cost.currency == "USD"

def test_attribution_record_immutability():
    cost = CurrencyAmount(Decimal("0.135"), "USD")
    details = CostCalculation(1000, 2000, Decimal("15.00"), Decimal("60.00"))
    
    record = AttributionRecord(
        attribution_id="attr-123",
        execution_id="exec-456",
        trace_id="trace-789",
        calculated_cost=cost,
        calculation_details=details,
        research_run_id="run-1",
        thesis_id="thesis-1",
        worker_id="worker-1",
        portfolio_id="port-1",
        strategy_id="strat-1",
        extended_dimensions={"extra": "value"}
    )
    
    assert record.attribution_id == "attr-123"
    assert record.execution_id == "exec-456"
    assert record.research_run_id == "run-1"
    assert record.extended_dimensions == {"extra": "value"}

    with pytest.raises(TypeError):
        record.attribution_id = "new-id"
    with pytest.raises(TypeError):
        record.research_run_id = "new-run"

def test_attribution_adjustment_immutability():
    cost = CurrencyAmount(Decimal("0.05"), "USD")
    adj = AttributionAdjustment(
        adjustment_id="adj-1",
        original_attribution_id="attr-123",
        adjustment_amount=cost,
        adjustment_reason="billing_correction"
    )
    
    assert adj.adjustment_id == "adj-1"
    assert adj.original_attribution_id == "attr-123"
    assert adj.adjustment_amount.amount == Decimal("0.05")

    with pytest.raises(TypeError):
        adj.adjustment_id = "new-adj"
    with pytest.raises(TypeError):
        adj.adjustment_reason = "new-reason"

def test_dimension_validation():
    cost = CurrencyAmount(Decimal("0.1"), "USD")
    details = CostCalculation(10, 10, Decimal("1"), Decimal("1"))
    
    bad_ext = {f"k{i}": "v" for i in range(25)}
    with pytest.raises(ValueError):
        AttributionRecord(
            attribution_id="attr-1",
            execution_id="exec-1",
            trace_id="trace-1",
            calculated_cost=cost,
            calculation_details=details,
            extended_dimensions=bad_ext
        )

    bad_key = {"a" * 130: "v"}
    with pytest.raises(ValueError):
        AttributionRecord(
            attribution_id="attr-1",
            execution_id="exec-1",
            trace_id="trace-1",
            calculated_cost=cost,
            calculation_details=details,
            extended_dimensions=bad_key
        )

    bad_val = {"k": "v" * 130}
    with pytest.raises(ValueError):
        AttributionRecord(
            attribution_id="attr-1",
            execution_id="exec-1",
            trace_id="trace-1",
            calculated_cost=cost,
            calculation_details=details,
            extended_dimensions=bad_val
        )

def test_pricing_snapshot_persistence():
    cost = CurrencyAmount(Decimal("0.135"), "USD")
    details = CostCalculation(1000, 2000, Decimal("15.00"), Decimal("60.00"))
    
    record = AttributionRecord(
        attribution_id="attr-123",
        execution_id="exec-456",
        trace_id="trace-789",
        calculated_cost=cost,
        calculation_details=details,
        research_run_id="run-1",
        extended_dimensions={"extra": "value"}
    )
    
    d = record.to_dict()
    assert d["attribution_id"] == "attr-123"
    assert d["calculation_details"]["input_rate_per_1m"] == "15.00"
    
    rebuilt = AttributionRecord.from_dict(d)
    assert rebuilt.attribution_id == "attr-123"
    assert rebuilt.calculation_details.input_tokens == 1000
    assert rebuilt.calculation_details.input_rate_per_1m == Decimal("15.00")
    assert rebuilt.calculated_cost.amount == Decimal("0.135")
