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
    
    # save a new active record for deactivating by session
    rec2 = PerformanceAttributionRecord(
        record_id="r2",
        session_id="s1",
        decision_id="urn:decision:2",
        thesis_urn="urn:thesis:1",
        worker_urn="urn:worker:1",
        capability_urn="urn:capability:1",
        regime_urn="urn:regime:1",
        asset_urn="urn:asset:1",
        selection_return=Decimal("0.05"),
        allocation_return=Decimal("0.01"),
        execution_return=Decimal("0.01"),
        beta_return=Decimal("0.01"),
        attribution_version=1,
        is_active=True
    )
    repo.save(rec2)
    
    # test query methods
    assert len(repo.find_active_by_decision("urn:decision:1")) == 0
    assert len(repo.find_by_session("s1")) == 2
    assert len(repo.list_all()) == 2
    
    # deactivate by session
    repo.deactivate_by_session("s1")
    retrieved_invalidated = repo.find_by_id("r2", 1)
    assert retrieved_invalidated.is_active is False
    assert retrieved_invalidated.invalidated_by_version == 2
    
    repo.clear()
    assert len(repo.list_all()) == 0
    
    shutil.rmtree(dir_path)


def test_in_memory_record_repository_queries():
    repo = InMemoryPerformanceAttributionRepository()
    rec = PerformanceAttributionRecord(
        record_id="r1", session_id="s1", decision_id="urn:decision:1",
        thesis_urn="t", worker_urn="w", capability_urn="c", regime_urn="rg", asset_urn="a1",
        selection_return=Decimal("0.05"), allocation_return=Decimal("0.01"), execution_return=Decimal("0.01"),
        beta_return=Decimal("0.01"), attribution_version=1
    )
    repo.save(rec)
    
    assert len(repo.find_active_by_decision("urn:decision:1")) == 1
    assert len(repo.find_by_session("s1")) == 1
    assert len(repo.list_all()) == 1
    
    # deactivate by session
    repo.deactivate_by_session("s1")
    retrieved = repo.find_by_id("r1", 1)
    assert retrieved.is_active is False
    assert retrieved.invalidated_by_version == 2
    
    repo.clear()
    assert len(repo.list_all()) == 0


def test_in_memory_session_list_and_clear():
    """Cover InMemoryAttributionSessionRepository.list_all and clear (lines 38, 41)."""
    repo = InMemoryAttributionSessionRepository()
    
    # list_all and clear on empty repo
    assert repo.list_all() == []
    repo.clear()  # no-op on empty
    
    # Add sessions
    s1 = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    s2 = AttributionSession("s2", datetime(2026, 2, 1), datetime(2026, 2, 5))
    repo.save(s1)
    repo.save(s2)
    assert len(repo.list_all()) == 2
    
    repo.clear()
    assert len(repo.list_all()) == 0
    assert repo.get_by_id("s1") is None

def test_in_memory_record_find_by_id_miss():
    """Cover InMemoryPerformanceAttributionRepository.find_by_id returning None (line 62)."""
    repo = InMemoryPerformanceAttributionRepository()
    assert repo.find_by_id("nonexistent", 1) is None

def test_file_session_occ_conflict():
    """Cover FileAttributionSessionRepository OCC check (line 117)."""
    dir_path = ".karsa/test_file_session_occ/"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    
    repo = FileAttributionSessionRepository(storage_dir=dir_path)
    session = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5))
    repo.save(session)
    
    # Try saving with wrong version (stale)
    stale = AttributionSession("s1", datetime(2026, 1, 1), datetime(2026, 1, 5), aggregate_version=1)
    with pytest.raises(ConcurrencyConflictError):
        repo.save(stale)
    
    shutil.rmtree(dir_path)

def test_file_session_get_by_id_miss():
    """Cover FileAttributionSessionRepository.get_by_id returning None (line 126)."""
    dir_path = ".karsa/test_file_session_miss/"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    
    repo = FileAttributionSessionRepository(storage_dir=dir_path)
    assert repo.get_by_id("nonexistent") is None
    
    shutil.rmtree(dir_path)

def test_file_record_find_by_id_miss():
    """Cover FilePerformanceAttributionRepository.find_by_id returning None (line 171)."""
    dir_path = ".karsa/test_file_record_miss/"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    
    repo = FilePerformanceAttributionRepository(storage_dir=dir_path)
    assert repo.find_by_id("nonexistent", 1) is None
    
    shutil.rmtree(dir_path)

def test_file_record_save_duplicate():
    """Cover FilePerformanceAttributionRepository.save duplicate check (line 164)."""
    dir_path = ".karsa/test_file_record_dup/"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    
    repo = FilePerformanceAttributionRepository(storage_dir=dir_path)
    rec = PerformanceAttributionRecord(
        record_id="r1", session_id="s1", decision_id="d1", thesis_urn="t1",
        worker_urn="w1", capability_urn="c1", regime_urn="rg1", asset_urn="a1",
        selection_return=Decimal("0.0"), allocation_return=Decimal("0.0"),
        execution_return=Decimal("0.0"), beta_return=Decimal("0.0"),
        attribution_version=1
    )
    repo.save(rec)
    
    with pytest.raises(ValueError, match="already exists"):
        repo.save(rec)
    
    shutil.rmtree(dir_path)


