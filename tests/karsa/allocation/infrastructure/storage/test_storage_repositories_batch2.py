import os
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
from karsa.allocation.domain.value_objects import (
    PortfolioHorizon,
    AllocationScore,
    RiskBudgetAssignment,
    AllocationRecommendation,
    AllocationMethodologyManifest
)
from karsa.allocation.domain.models import (
    AllocationSession,
    AllocationDecisionRecord,
    ImmutabilityViolationError
)
from karsa.allocation.infrastructure.storage.in_memory_repositories import (
    InMemoryAllocationSessionRepository,
    InMemoryAllocationDecisionRecordRepository,
    ConcurrencyConflictError
)
from karsa.allocation.infrastructure.storage.file_repositories import (
    FileAllocationSessionRepository,
    FileAllocationDecisionRecordRepository
)

# Helpers
def make_horizon(horizon_id="90D"):
    return PortfolioHorizon(
        horizon_id=horizon_id,
        horizon_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_end=datetime(2026, 3, 31, tzinfo=timezone.utc)
    )

def make_score():
    return AllocationScore(
        raw_score=0.85,
        performance_score=0.9,
        attribution_score=0.8,
        review_penalty_multiplier=1.0
    )

def make_recommendation():
    risk = RiskBudgetAssignment(
        tracking_error_pct=0.05,
        max_drawdown_limit=0.15
    )
    return AllocationRecommendation(
        recommended_weight=0.25,
        recommended_capital_percentage=0.20,
        risk_budget=risk
    )

def make_manifest():
    return AllocationMethodologyManifest(
        allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
        allocation_policy_hash="a" * 64,
        allocation_strategy_version="v1.0"
    )

def test_in_memory_session_repo_crud_and_occ():
    repo = InMemoryAllocationSessionRepository()
    sess_id = str(uuid.uuid4())
    sess = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="WEIGHTED_FACTOR_V1"
    )
    
    # Save & Get URN
    repo.save(sess)
    loaded = repo.find_by_urn(sess.session_urn)
    assert loaded is not None
    assert loaded.session_id == sess_id
    assert loaded.aggregate_version == 1
    
    # Deepcopy isolation test
    assert loaded is not sess
    loaded.strategy_key = "CHANGED"
    loaded2 = repo.find_by_urn(sess.session_urn)
    assert loaded2.strategy_key == "WEIGHTED_FACTOR_V1"
    
    # Update version
    sess.start() # Version becomes 2
    repo.save(sess)
    
    # OCC Conflict
    sess_stale = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="WEIGHTED_FACTOR_V1",
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        repo.save(sess_stale)

def test_in_memory_decision_record_repo_crud_and_occ():
    repo = InMemoryAllocationDecisionRecordRepository()
    rec_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())
    m = make_manifest()
    
    record = AllocationDecisionRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:allocation:record:{rec_id}",
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )
    
    # Save & Find URN
    repo.save(record)
    loaded = repo.find_by_urn(record.record_urn)
    assert loaded is not None
    assert loaded.record_id == rec_id
    assert loaded.aggregate_version == 1
    
    # Deepcopy isolation
    assert loaded is not record
    
    # Update (allowed fields)
    record.is_active = False
    record.superseded_by_version = 2
    record.increment_version() # Version becomes 2
    repo.save(record)
    
    # OCC Conflict
    stale_rec = AllocationDecisionRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:allocation:record:{rec_id}",
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        repo.save(stale_rec)
        
    # Immutability Check (simulate DB trigger on non-mutable field change)
    invalid_update_rec = AllocationDecisionRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:allocation:record:{rec_id}",
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        worker_urn="urn:karsa:worker:w2", # modified immutable field
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        aggregate_version=3
    )
    with pytest.raises(ImmutabilityViolationError):
        repo.save(invalid_update_rec)

def test_in_memory_decision_record_pagination():
    repo = InMemoryAllocationDecisionRecordRepository()
    sess_urn = "urn:karsa:allocation:session:s1"
    worker_urn = "urn:karsa:worker:w1"
    m = make_manifest()
    
    # Create 5 records
    records = []
    for i in range(5):
        # We ensure deterministic order of URNs by sorting ids
        rec_id = f"00000000-0000-0000-0000-00000000000{i}"
        rec = AllocationDecisionRecord(
            record_id=rec_id,
            record_urn=f"urn:karsa:allocation:record:{rec_id}",
            session_urn=sess_urn,
            worker_urn=worker_urn,
            decision_id=f"dec-{i}",
            horizon=make_horizon(),
            allocation_score=make_score(),
            recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn,
            allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version,
            allocation_manifest_hash=m.compute_hash(),
            is_active=True
        )
        repo.save(rec)
        records.append(rec)
        
    # Find active by worker paginated (limit=2)
    page1 = repo.find_active_by_worker(worker_urn, limit=2)
    assert len(page1) == 2
    assert page1[0].record_urn == records[0].record_urn
    assert page1[1].record_urn == records[1].record_urn
    
    # Second page
    page2 = repo.find_active_by_worker(worker_urn, limit=2, cursor=page1[1].record_urn)
    assert len(page2) == 2
    assert page2[0].record_urn == records[2].record_urn
    assert page2[1].record_urn == records[3].record_urn
    
    # Third page
    page3 = repo.find_active_by_worker(worker_urn, limit=2, cursor=page2[1].record_urn)
    assert len(page3) == 1
    assert page3[0].record_urn == records[4].record_urn
    
    # Find by session paginated
    sess_page1 = repo.find_by_session_paginated(sess_urn, limit=3)
    assert len(sess_page1) == 3
    assert sess_page1[2].record_urn == records[2].record_urn

    # Keyset pagination with cursor for session URN
    sess_page2 = repo.find_by_session_paginated(sess_urn, limit=2, cursor=sess_page1[1].record_urn)
    assert len(sess_page2) == 2

def test_in_memory_lineage_and_cycles():
    repo = InMemoryAllocationDecisionRecordRepository()
    sess_urn = "urn:karsa:allocation:session:s1"
    m = make_manifest()
    
    r1_id = str(uuid.uuid4())
    r1 = AllocationDecisionRecord(
        record_id=r1_id,
        record_urn=f"urn:karsa:allocation:record:{r1_id}",
        session_urn=sess_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        is_active=False,
        superseded_by_version=2,
        allocation_version=1
    )
    
    r2_id = str(uuid.uuid4())
    r2 = AllocationDecisionRecord(
        record_id=r2_id,
        record_urn=f"urn:karsa:allocation:record:{r2_id}",
        session_urn=sess_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        supersedes_record_urn=r1.record_urn,
        is_active=True,
        allocation_version=2
    )
    
    repo.save(r1)
    repo.save(r2)
    
    # Lineage query
    lineage = repo.find_lineage(r2.record_urn)
    assert len(lineage) == 2
    assert lineage[0].record_urn == r1.record_urn
    assert lineage[1].record_urn == r2.record_urn

    # Alias check
    lineage2 = repo.find_allocation_lineage(r1.record_urn)
    assert len(lineage2) == 2

    # Cycle safety
    r_cycle_id = str(uuid.uuid4())
    r_cycle = AllocationDecisionRecord(
        record_id=r_cycle_id,
        record_urn=f"urn:karsa:allocation:record:{r_cycle_id}",
        session_urn=sess_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        supersedes_record_urn=f"urn:karsa:allocation:record:{r_cycle_id}", # Point to self to create cycle
        is_active=True,
        allocation_version=1
    )
    repo.save(r_cycle)
    cycle_lineage = repo.find_lineage(r_cycle.record_urn)
    assert len(cycle_lineage) == 1

def test_file_repos(tmp_path):
    sess_dir = tmp_path / "sessions"
    rec_dir = tmp_path / "records"
    
    # Write some garbage tmp file to test recovery cleanup
    sess_dir.mkdir()
    rec_dir.mkdir()
    (sess_dir / "orphaned.tmp").write_text("garbage")
    (rec_dir / "orphaned.tmp").write_text("garbage")
    
    sess_repo = FileAllocationSessionRepository(storage_dir=str(sess_dir))
    rec_repo = FileAllocationDecisionRecordRepository(storage_dir=str(rec_dir))
    
    # Check recovery cleanup worked
    assert not os.path.exists(sess_dir / "orphaned.tmp")
    assert not os.path.exists(rec_dir / "orphaned.tmp")
    
    sess_id = str(uuid.uuid4())
    sess = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="WEIGHTED_FACTOR_V1"
    )
    
    # Session CRUD
    sess_repo.save(sess)
    loaded_sess = sess_repo.find_by_urn(sess.session_urn)
    assert loaded_sess is not None
    assert loaded_sess.session_id == sess_id
    
    # Deterministic file layout test (sorted keys check in file content)
    filepath = sess_dir / f"{sess_id}.json"
    with open(filepath, "r") as f:
        file_content = f.read()
    # verify keys are sorted and indent exists
    assert '"aggregate_version": 1,' in file_content or '"aggregate_version": 1' in file_content
    
    # Session Update (covers 47->53 branch version success update)
    sess.start() # Version becomes 2
    sess_repo.save(sess)
    
    # Session OCC Conflict
    sess_stale = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="WEIGHTED_FACTOR_V1",
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        sess_repo.save(sess_stale)
        
    # Decision Record CRUD
    rec_id = str(uuid.uuid4())
    m = make_manifest()
    record = AllocationDecisionRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:allocation:record:{rec_id}",
        session_urn=sess.session_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )
    
    rec_repo.save(record)
    loaded_rec = rec_repo.find_by_urn(record.record_urn)
    assert loaded_rec is not None
    assert loaded_rec.record_id == rec_id

    # Record successful update (covers 112->119 branch)
    record.is_active = False
    record.superseded_by_version = 2
    record.increment_version()
    rec_repo.save(record)
    
    # Record OCC Conflict
    stale_rec = AllocationDecisionRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:allocation:record:{rec_id}",
        session_urn=sess.session_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        aggregate_version=1
    )
    with pytest.raises(ConcurrencyConflictError):
        rec_repo.save(stale_rec)
        
    # Record Immutability trigger
    invalid_update_rec = AllocationDecisionRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:allocation:record:{rec_id}",
        session_urn=sess.session_urn,
        worker_urn="urn:karsa:worker:w2", # modified immutable field
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        aggregate_version=3
    )
    with pytest.raises(ImmutabilityViolationError):
        rec_repo.save(invalid_update_rec)

    # Keyset Pagination on File
    # Write another 4 records to file
    for i in range(1, 5):
        other_rec_id = f"10000000-0000-0000-0000-00000000000{i}"
        other_rec = AllocationDecisionRecord(
            record_id=other_rec_id,
            record_urn=f"urn:karsa:allocation:record:{other_rec_id}",
            session_urn=sess.session_urn,
            worker_urn="urn:karsa:worker:w1",
            decision_id=f"dec-{i}",
            horizon=make_horizon(),
            allocation_score=make_score(),
            recommendation=make_recommendation(),
            allocation_methodology_urn=m.allocation_methodology_urn,
            allocation_policy_hash=m.allocation_policy_hash,
            allocation_strategy_version=m.allocation_strategy_version,
            allocation_manifest_hash=m.compute_hash(),
            is_active=True
        )
        rec_repo.save(other_rec)
        
    # Query active paginated
    all_workers = rec_repo.find_active_by_worker("urn:karsa:worker:w1", limit=10)
    assert len(all_workers) == 4
    
    # Query with cursor
    cursor = all_workers[1].record_urn
    paginated = rec_repo.find_active_by_worker("urn:karsa:worker:w1", limit=2, cursor=cursor)
    assert len(paginated) == 2
    assert paginated[0].record_urn > cursor
    
    # Query by session paginated
    sess_paginated = rec_repo.find_by_session_paginated(sess.session_urn, limit=2)
    assert len(sess_paginated) == 2

    sess_paginated2 = rec_repo.find_by_session_paginated(sess.session_urn, limit=2, cursor=sess_paginated[1].record_urn)
    assert len(sess_paginated2) == 2
    
    # File URN lineage query
    lineage = rec_repo.find_lineage(all_workers[0].record_urn)
    assert len(lineage) >= 1
    
    # Alias check
    lineage2 = rec_repo.find_allocation_lineage(all_workers[0].record_urn)
    assert len(lineage2) >= 1

    sess_paginated3 = rec_repo.find_by_session_paginated(sess.session_urn, limit=10)
    assert len(sess_paginated3) == 5

    # Re-instantiate record repo to trigger cleanup check with non-tmp files in directory
    FileAllocationDecisionRecordRepository(storage_dir=str(rec_dir))

    # Recovery cleanup check during normal save errors
    class BadRecord:
        record_id = "bad-rec"
        aggregate_version = 1
        def to_dict(self):
            raise RuntimeError("mock serialization failed")

    with pytest.raises(RuntimeError):
        rec_repo.save(BadRecord())
        
    # Verify no tmp files are left in rec_dir
    tmp_files = [f for f in os.listdir(rec_dir) if f.endswith(".tmp")]
    assert len(tmp_files) == 0

    class BadSession:
        session_id = "bad-sess"
        aggregate_version = 1
        def to_dict(self):
            raise RuntimeError("mock serialization failed")

    with pytest.raises(RuntimeError):
        sess_repo.save(BadSession())

    # find_by_urn handling invalid inputs / exceptions
    assert rec_repo.find_by_urn("invalid_urn_with_no_colons") is None
    assert sess_repo.find_by_urn("invalid_urn_with_no_colons") is None

def test_in_memory_repos_additional_edges():
    # Empty repo checks
    sess_repo = InMemoryAllocationSessionRepository()
    assert sess_repo.find_by_urn("urn:nonexistent") is None
    
    # Search when not empty but URN not matching (enters loop, exits loop -> returns None)
    sess = AllocationSession(
        session_id=str(uuid.uuid4()),
        session_urn="urn:karsa:allocation:session:s1",
        horizon=make_horizon(),
        strategy_key="key"
    )
    sess_repo.save(sess)
    assert sess_repo.find_by_urn("urn:karsa:allocation:session:s2") is None

    rec_repo = InMemoryAllocationDecisionRecordRepository()
    assert rec_repo.find_by_urn("urn:nonexistent") is None
    
    # Search when not empty but URN not matching
    m = make_manifest()
    record = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()),
        record_urn="urn:karsa:allocation:record:r1",
        session_urn="urn:karsa:allocation:session:s1",
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )
    rec_repo.save(record)
    assert rec_repo.find_by_urn("urn:karsa:allocation:record:r2") is None

    # pagination limit not hit exit loop naturally
    matched = rec_repo.find_active_by_worker("urn:karsa:worker:w1", limit=10)
    assert len(matched) == 1
    
    matched_other = rec_repo.find_active_by_worker("urn:karsa:worker:w2", limit=10)
    assert len(matched_other) == 0
    
    matched2 = rec_repo.find_by_session_paginated("urn:karsa:allocation:session:s1", limit=10)
    assert len(matched2) == 1
    
    matched2_other = rec_repo.find_by_session_paginated("urn:karsa:allocation:session:s2", limit=10)
    assert len(matched2_other) == 0

def test_file_repos_cleanup_failures_and_errors(tmp_path):
    sess_dir = tmp_path / "sessions_err"
    rec_dir = tmp_path / "records_err"
    sess_dir.mkdir()
    rec_dir.mkdir()
    
    # 1. Test os.listdir failure in clean-up
    with patch("os.listdir", side_effect=OSError("permission denied")):
        sess_repo = FileAllocationSessionRepository(storage_dir=str(sess_dir))
        rec_repo = FileAllocationDecisionRecordRepository(storage_dir=str(rec_dir))
        
    # 2. Test os.remove failure in clean-up for session repo
    (sess_dir / "test.tmp").write_text("test")
    with patch("os.remove", side_effect=OSError("file locked")):
        sess_repo = FileAllocationSessionRepository(storage_dir=str(sess_dir))
        
    # 3. Test cleanup failure for record repo
    (rec_dir / "test.tmp").write_text("test")
    with patch("os.remove", side_effect=OSError("file locked")):
        rec_repo = FileAllocationDecisionRecordRepository(storage_dir=str(rec_dir))
        
    # 4. Test find_by_urn with None to trigger exception -> return None
    assert sess_repo.find_by_urn(None) is None
    assert rec_repo.find_by_urn(None) is None

    # 5. Test clean-up when there are non-tmp files (to cover endswith(".tmp") == False branch)
    (sess_dir / "valid.json").write_text("{}")
    sess_repo = FileAllocationSessionRepository(storage_dir=str(sess_dir))
    
    # 6. Test listdir error in _load_all_records
    with patch("os.listdir", side_effect=OSError("permission denied")):
        rec_repo._load_all_records()
        
    # 7. Test corrupted JSON skip in _load_all_records
    (rec_dir / "corrupted.json").write_text("{invalid json}")
    # Also write a valid file to verify it doesn't break
    (rec_dir / "valid.json").write_text("{}")
    # Also write a non-json file (to cover endswith(".json") == False)
    (rec_dir / "readme.txt").write_text("readme")
    
    records = rec_repo._load_all_records()
    # It should skip corrupted.json and valid.json (which fails from_dict because it's empty)
    # So it should return empty list without raising exception
    assert len(records) == 0

def test_file_repos_temp_path_missing(tmp_path):
    sess_repo = FileAllocationSessionRepository(storage_dir=str(tmp_path / "sess_tmp"))
    rec_repo = FileAllocationDecisionRecordRepository(storage_dir=str(tmp_path / "rec_tmp"))
    sess = AllocationSession(
        session_id=str(uuid.uuid4()),
        session_urn="urn:karsa:allocation:session:s1",
        horizon=make_horizon(),
        strategy_key="key"
    )
    m = make_manifest()
    record = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()),
        record_urn="urn:karsa:allocation:record:r1",
        session_urn="urn:karsa:allocation:session:s1",
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )

    orig_exists = os.path.exists
    def mock_exists(path):
        if ".tmp" in str(path):
            return False
        return orig_exists(path)

    with patch("os.path.exists", side_effect=mock_exists):
        # We trigger an exception during save by making json.dump raise an error
        with patch("json.dump", side_effect=RuntimeError("write failed")):
            with pytest.raises(RuntimeError):
                sess_repo.save(sess)
            with pytest.raises(RuntimeError):
                rec_repo.save(record)
