import os
import shutil
import pytest
from datetime import datetime
from decimal import Decimal
from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord
from karsa.attribution.infrastructure.repositories import (
    InMemoryAttributionSessionRepository,
    InMemoryPerformanceAttributionRepository,
    FileAttributionSessionRepository,
    FilePerformanceAttributionRepository
)
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

def test_in_memory_session_repository():
    repo = InMemoryAttributionSessionRepository()
    
    session = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    repo.save(session)
    
    retrieved = repo.get_by_id("s1")
    assert retrieved is not None
    assert retrieved.compounding_strategy == "FRONGELLO"
    
    # Save update with correct version
    retrieved.transition_to("COMPUTING")
    repo.save(retrieved)
    
    # Save update with WRONG version -> ConcurrencyConflictError
    session_stale = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5), aggregate_version=1)
    with pytest.raises(ConcurrencyConflictError):
        repo.save(session_stale)

def test_in_memory_record_repository():
    repo = InMemoryPerformanceAttributionRepository()
    
    rec = PerformanceAttributionRecord(
        record_id="r1",
        session_id="s1",
        decision_id="urn:decision:1",
        thesis_urn="urn:thesis:1",
        worker_urn="urn:worker:1",
        capability_urn="urn:capability:1",
        regime_urn="urn:regime:1",
        asset_urn="urn:asset:1",
        selection_return=Decimal("0.05"),
        allocation_return=Decimal("0.01"),
        execution_return=Decimal("0.01"),
        beta_return=Decimal("0.01"),
        attribution_version=1
    )
    repo.save(rec)
    
    # saving same version again -> ValueError
    with pytest.raises(ValueError):
        repo.save(rec)

def test_file_session_repository():
    dir_path = ".karsa/test_file_session_repo/"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        
    repo = FileAttributionSessionRepository(storage_dir=dir_path)
    session = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    repo.save(session)
    
    retrieved = repo.get_by_id("s1")
    assert retrieved is not None
    assert retrieved.horizon_start == datetime(2026, 1, 1)
    
    shutil.rmtree(dir_path)

def test_file_record_repository():
    dir_path = ".karsa/test_file_record_repo/"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        
    repo = FilePerformanceAttributionRepository(storage_dir=dir_path)
    rec = PerformanceAttributionRecord(
        record_id="r1",
        session_id="s1",
        decision_id="urn:decision:1",
        thesis_urn="urn:thesis:1",
        worker_urn="urn:worker:1",
        capability_urn="urn:capability:1",
        regime_urn="urn:regime:1",
        asset_urn="urn:asset:1",
        selection_return=Decimal("0.05"),
        allocation_return=Decimal("0.01"),
        execution_return=Decimal("0.01"),
        beta_return=Decimal("0.01"),
        attribution_version=1
    )
    repo.save(rec)
    
    retrieved = repo.find_by_id("r1", 1)
    assert retrieved is not None
    assert retrieved.selection_return == Decimal("0.05")
    
    # deactivate old versions
    repo.deactivate_old_versions("urn:decision:1", 2)
    retrieved_updated = repo.find_by_id("r1", 1)
    assert retrieved_updated.is_active is False
    
    shutil.rmtree(dir_path)
