import os
import shutil
import pytest
from decimal import Decimal
from karsa.attribution.domain.model.models import CurrencyAmount, CostCalculation, AttributionRecord, AttributionAdjustment
from karsa.attribution.infrastructure.repositories import (
    InMemoryAttributionRecordRepository,
    InMemoryAttributionAdjustmentRepository,
    FileAttributionRecordRepository,
    FileAttributionAdjustmentRepository
)

def test_in_memory_repositories():
    rec_repo = InMemoryAttributionRecordRepository()
    adj_repo = InMemoryAttributionAdjustmentRepository()

    cost = CurrencyAmount(Decimal("0.05"), "USD")
    details = CostCalculation(100, 100, Decimal("1.0"), Decimal("1.0"))
    record = AttributionRecord("attr-1", "exec-1", "trace-1", cost, details, research_run_id="run-1")
    rec_repo.save(record)

    adj = AttributionAdjustment("adj-1", "attr-1", CurrencyAmount(Decimal("0.01"), "USD"), "test")
    adj_repo.save(adj)

    assert rec_repo.find_by_attribution_id("attr-1") == record
    assert rec_repo.find_by_execution_id("exec-1") == record
    assert len(adj_repo.find_by_original_id("attr-1")) == 1
    assert adj_repo.find_by_original_id("attr-1")[0] == adj

def test_file_repositories():
    test_record_dir = ".karsa/test_attribution/records/"
    test_adj_dir = ".karsa/test_attribution/adjustments/"

    if os.path.exists(".karsa/test_attribution/"):
        shutil.rmtree(".karsa/test_attribution/")

    rec_repo = FileAttributionRecordRepository(storage_dir=test_record_dir)
    adj_repo = FileAttributionAdjustmentRepository(storage_dir=test_adj_dir)

    cost = CurrencyAmount(Decimal("0.12"), "USD")
    details = CostCalculation(200, 200, Decimal("2.0"), Decimal("2.0"))
    record = AttributionRecord("attr-file", "exec-file", "trace-file", cost, details, thesis_id="thesis-file")
    rec_repo.save(record)

    adj = AttributionAdjustment("adj-file", "attr-file", CurrencyAmount(Decimal("-0.02"), "USD"), "drift")
    adj_repo.save(adj)

    rebuilt_rec = rec_repo.find_by_attribution_id("attr-file")
    assert rebuilt_rec is not None
    assert rebuilt_rec.attribution_id == "attr-file"
    assert rebuilt_rec.execution_id == "exec-file"
    assert rebuilt_rec.thesis_id == "thesis-file"
    assert rebuilt_rec.calculated_cost.amount == Decimal("0.12")
    assert rebuilt_rec.calculation_details.input_tokens == 200

    rebuilt_exec = rec_repo.find_by_execution_id("exec-file")
    assert rebuilt_exec is not None
    assert rebuilt_exec.attribution_id == "attr-file"

    adjs = adj_repo.find_by_original_id("attr-file")
    assert len(adjs) == 1
    assert adjs[0].adjustment_id == "adj-file"
    assert adjs[0].adjustment_amount.amount == Decimal("-0.02")

    rec_repo.clear()
    adj_repo.clear()
    assert len(rec_repo.list_all()) == 0
    assert len(adj_repo.list_all()) == 0

    if os.path.exists(".karsa/test_attribution/"):
        shutil.rmtree(".karsa/test_attribution/")
