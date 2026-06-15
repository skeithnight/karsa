import pytest
import os
import tempfile
import threading
from decimal import Decimal
from pathlib import Path

from src.karsa.regime.domain.models import RegimeSession, RegimeSnapshot, RegimeTransition
from src.karsa.regime.domain.value_objects import RegimeClassification, SignalConfidenceScore
from src.karsa.regime.domain.repositories import ConcurrencyError, ImmutableUpdateError
from src.karsa.regime.domain.lineage import LineageCycleError

from src.karsa.regime.infrastructure.storage.in_memory_repositories import (
    InMemoryRegimeSessionRepository, InMemoryRegimeSnapshotRepository, InMemoryRegimeTransitionRepository
)
from src.karsa.regime.infrastructure.storage.file_repositories import (
    FileRegimeSessionRepository, FileRegimeSnapshotRepository, FileRegimeTransitionRepository
)

def create_dummy_snapshot(urn, seg, hor, dt):
    return RegimeSnapshot(
        snapshot_urn=urn, segment_urn=seg, horizon_urn=hor, snapshot_date=dt,
        regime_classification=RegimeClassification("BULL", "LOW", "HIGH"),
        confidence_score=SignalConfidenceScore(Decimal('1.0')),
        regime_manifest_hash="rhash", evidence_manifest_hash="ehash", methodology_metadata={}
    )

def create_dummy_transition(urn, v=1, super_urn=None):
    return RegimeTransition(
        transition_urn=urn,
        from_regime=RegimeClassification("BULL", "LOW", "HIGH"),
        to_regime=RegimeClassification("BEAR", "HIGH", "LOW"),
        transition_manifest_hash="hash",
        supersedes_transition_urn=super_urn,
        aggregate_version=v
    )

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td

@pytest.mark.parametrize("repo_cls", [InMemoryRegimeSessionRepository, FileRegimeSessionRepository])
def test_session_occ(repo_cls, temp_dir):
    repo = repo_cls() if repo_cls == InMemoryRegimeSessionRepository else repo_cls(temp_dir)
    
    s = RegimeSession("urn:sess1", aggregate_version=1)
    repo.save(s)
    
    s.start_analyzing()
    repo.save(s) # v2
    
    s_conflict = RegimeSession("urn:sess1", aggregate_version=1)
    s_conflict.start_analyzing() # v2, but expected v3
    s_conflict.start_analyzing() # bump to v3 so it passes OCC wait, no, if I try to save an older version:
    
    s_old = RegimeSession("urn:sess1", aggregate_version=1)
    with pytest.raises(ConcurrencyError):
        repo.save(s_old)

@pytest.mark.parametrize("repo_cls", [InMemoryRegimeSnapshotRepository, FileRegimeSnapshotRepository])
def test_snapshot_immutable_and_natural_key(repo_cls, temp_dir):
    repo = repo_cls() if repo_cls == InMemoryRegimeSnapshotRepository else repo_cls(temp_dir)
    
    s1 = create_dummy_snapshot("urn:snap1", "seg1", "hor1", "2026-06-15")
    repo.save(s1)
    
    with pytest.raises(ImmutableUpdateError):
        repo.save(s1)
        
    s2 = create_dummy_snapshot("urn:snap2", "seg1", "hor1", "2026-06-15")
    with pytest.raises(ImmutableUpdateError):
        repo.save(s2)

    found = repo.find_by_natural_key("seg1", "hor1", "2026-06-15")
    assert found is not None
    assert found.snapshot_urn == "urn:snap1"

@pytest.mark.parametrize("repo_cls", [InMemoryRegimeSnapshotRepository, FileRegimeSnapshotRepository])
def test_snapshot_pagination(repo_cls, temp_dir):
    repo = repo_cls() if repo_cls == InMemoryRegimeSnapshotRepository else repo_cls(temp_dir)
    
    repo.save(create_dummy_snapshot("urn:snap1", "seg1", "hor1", "2026-06-15"))
    repo.save(create_dummy_snapshot("urn:snap2", "seg1", "hor1", "2026-06-16"))
    repo.save(create_dummy_snapshot("urn:snap3", "seg1", "hor2", "2026-06-15"))
    
    res = repo.find_by_segment_paginated("seg1", limit=1)
    assert len(res) == 1
    assert res[0].snapshot_urn == "urn:snap1"
    
    res2 = repo.find_by_segment_paginated("seg1", limit=1, last_date="2026-06-15", last_urn="urn:snap1")
    assert len(res2) == 1
    assert res2[0].snapshot_urn == "urn:snap2"
    
    res_hor = repo.find_by_horizon_paginated("hor1", limit=2)
    assert len(res_hor) == 2

@pytest.mark.parametrize("repo_cls", [InMemoryRegimeTransitionRepository, FileRegimeTransitionRepository])
def test_transition_lineage_and_cycle(repo_cls, temp_dir):
    repo = repo_cls() if repo_cls == InMemoryRegimeTransitionRepository else repo_cls(temp_dir)
    
    t1 = create_dummy_transition("urn:t1", v=1, super_urn="urn:t2")
    t2 = create_dummy_transition("urn:t2", v=1, super_urn=None)
    repo.save(t1)
    repo.save(t2)
    
    lineage = repo.find_transition_lineage("urn:t1")
    assert len(lineage) == 2
    
    t3 = create_dummy_transition("urn:t3", v=1, super_urn="urn:t4")
    t4 = create_dummy_transition("urn:t4", v=1, super_urn="urn:t3")
    repo.save(t3)
    repo.save(t4)
    
    with pytest.raises(LineageCycleError):
        repo.find_transition_lineage("urn:t3")

def test_file_atomic_write(temp_dir):
    repo = FileRegimeSessionRepository(temp_dir)
    s = RegimeSession("urn:sess_atomic", aggregate_version=1)
    
    def save_task():
        repo.save(s)

    threads = [threading.Thread(target=save_task) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert repo.find_by_urn("urn:sess_atomic") is not None
    # Check no temp files left
    temp_files = list(Path(temp_dir).glob("*.tmp.*"))
    assert len(temp_files) == 0

def test_concurrent_access():
    repo = InMemoryRegimeSessionRepository()
    s = RegimeSession("urn:sess_conc", aggregate_version=1)
    repo.save(s)
    
    def read_task():
        for _ in range(100):
            repo.find_by_urn("urn:sess_conc")
            
    threads = [threading.Thread(target=read_task) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
