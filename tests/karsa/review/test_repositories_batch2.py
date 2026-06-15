import os
import json
import pytest
import uuid
import shutil
import tempfile
from datetime import datetime, timezone
from karsa.review.domain.models import (
    ReviewSession,
    ReviewRecord,
    PostMortemRecord,
    ImmutabilityViolationError
)
from karsa.review.domain.value_objects import (
    DecisionQualityAssessment,
    FailureClassification,
    SuccessClassification,
    ImprovementRecommendation,
    ReviewMethodologyManifest
)
from karsa.review.infrastructure.repositories_batch2 import (
    InMemoryReviewSessionRepository,
    InMemoryReviewRecordRepository,
    InMemoryPostMortemRecordRepository,
    FileReviewSessionRepository,
    FileReviewRecordRepository,
    FilePostMortemRecordRepository,
    ConcurrencyConflictError
)

@pytest.fixture
def temp_storage():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


# Helper constructors
def make_session(status="INITIATED"):
    sess_id = str(uuid.uuid4())
    return ReviewSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:review:session:{sess_id}",
        horizon_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        raw_input_manifest_hash="a" * 64,
        status=status
    )

def make_record(session_urn, decision_id="dec-1", worker_urn="urn:karsa:worker:w1", review_version=1):
    rec_id = str(uuid.uuid4())
    manifest = ReviewMethodologyManifest("urn:karsa:m:1", "b" * 64, "v1", "gpt-4")
    dq = DecisionQualityAssessment(0.8, 0.9, 0.1)
    return ReviewRecord(
        record_id=rec_id,
        record_urn=f"urn:karsa:review:record:{rec_id}",
        session_urn=session_urn,
        decision_id=decision_id,
        worker_urn=worker_urn,
        review_methodology_urn="urn:karsa:m:1",
        review_policy_hash="b" * 64,
        review_prompt_version="v1",
        reviewer_model_version="gpt-4",
        review_methodology_manifest_hash=manifest.compute_hash(),
        decision_quality=dq,
        reviewed_at=datetime.now(timezone.utc),
        review_version=review_version
    )

def make_postmortem(session_urn, decision_id="dec-1", postmortem_version=1):
    pm_id = str(uuid.uuid4())
    fc = FailureClassification(True, False, False, False, False)
    sc = SuccessClassification(False, True, False)
    rec = ImprovementRecommendation("EXECUTION_WARNING", "exec", "LOW")
    return PostMortemRecord(
        postmortem_id=pm_id,
        postmortem_urn=f"urn:karsa:postmortem:record:{pm_id}",
        session_urn=session_urn,
        decision_id=decision_id,
        consensus_methodology_urn="urn:karsa:consensus:s1",
        consensus_policy_hash="c" * 64,
        input_review_record_urns=["urn:karsa:review:record:r1"],
        failure_classification=fc,
        success_classification=sc,
        recommendation=rec,
        created_at=datetime.now(timezone.utc),
        postmortem_version=postmortem_version
    )


# 1. SAVE / LOAD & NOT FOUND TESTS

@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewSessionRepository, None),
    (FileReviewSessionRepository, "temp_storage")
])
def test_session_save_load(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    session = make_session()
    repo.save(session)
    
    # Find by ID
    loaded = repo.find_by_id(session.session_id)
    assert loaded is not None
    assert loaded.session_urn == session.session_urn
    
    # Find by URN
    loaded_urn = repo.find_by_urn(session.session_urn)
    assert loaded_urn is not None
    assert loaded_urn.session_id == session.session_id
    
    # Not found behavior
    assert repo.find_by_id("non-existent") is None
    assert repo.find_by_urn("urn:karsa:review:session:non-existent") is None


@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewRecordRepository, None),
    (FileReviewRecordRepository, "temp_storage")
])
def test_record_save_load(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    sess = make_session()
    record = make_record(sess.session_urn)
    repo.save(record)
    
    loaded = repo.find_by_id(record.record_id)
    assert loaded is not None
    assert loaded.record_urn == record.record_urn
    
    loaded_urn = repo.find_by_urn(record.record_urn)
    assert loaded_urn is not None
    assert loaded_urn.record_id == record.record_id
    
    assert repo.find_by_id("non-existent") is None
    assert repo.find_by_urn("urn:karsa:review:record:non-existent") is None


@pytest.mark.parametrize("adapter_class", [
    (InMemoryPostMortemRecordRepository, None),
    (FilePostMortemRecordRepository, "temp_storage")
])
def test_postmortem_save_load(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    sess = make_session()
    pm = make_postmortem(sess.session_urn)
    repo.save(pm)
    
    loaded = repo.find_by_id(pm.postmortem_id)
    assert loaded is not None
    assert loaded.postmortem_urn == pm.postmortem_urn
    
    loaded_urn = repo.find_by_urn(pm.postmortem_urn)
    assert loaded_urn is not None
    assert loaded_urn.postmortem_id == pm.postmortem_id
    
    assert repo.find_by_id("non-existent") is None
    assert repo.find_by_urn("urn:karsa:postmortem:record:non-existent") is None


# 2. OCC PROTECTIONS

@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewSessionRepository, None),
    (FileReviewSessionRepository, "temp_storage")
])
def test_session_occ(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    session = make_session()
    repo.save(session)
    
    # Modify session version manually to trigger OCC Conflict
    session.aggregate_version = 1  # Reset to 1 instead of incrementing
    with pytest.raises(ConcurrencyConflictError):
        repo.save(session)


# 3. IMMUTABILITY PRESERVATION

@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewRecordRepository, None),
    (FileReviewRecordRepository, "temp_storage")
])
def test_record_immutability_preservation(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    sess = make_session()
    record = make_record(sess.session_urn)
    repo.save(record)
    
    loaded = repo.find_by_id(record.record_id)
    
    # Try modifying core field
    with pytest.raises(ImmutabilityViolationError):
        loaded.decision_id = "new-dec"
        
    # Deactivate and save
    loaded.supersede(next_version=2)
    repo.save(loaded)
    
    refetched = repo.find_by_id(record.record_id)
    assert refetched.is_active is False
    assert refetched.superseded_by_version == 2


# 4. PAGINATION & CURSOR BEHAVIOR

@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewRecordRepository, None),
    (FileReviewRecordRepository, "temp_storage")
])
def test_record_pagination_and_cursors(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    sess = make_session()
    
    # Seed 5 records for the same session
    records = [make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1") for _ in range(5)]
    for r in records:
        repo.save(r)
        
    # Sort URNs alphabetically to know the expected order
    sorted_records = sorted(records, key=lambda x: x.record_urn)
    
    # Fetch page 1 (limit 2)
    p1 = repo.find_by_session_paginated(sess.session_urn, limit=2)
    assert len(p1) == 2
    assert p1[0].record_urn == sorted_records[0].record_urn
    assert p1[1].record_urn == sorted_records[1].record_urn
    
    # Fetch page 2 using cursor
    cursor = p1[1].record_urn
    p2 = repo.find_by_session_paginated(sess.session_urn, limit=2, cursor=cursor)
    assert len(p2) == 2
    assert p2[0].record_urn == sorted_records[2].record_urn
    assert p2[1].record_urn == sorted_records[3].record_urn
    
    # Fetch page 3
    cursor2 = p2[1].record_urn
    p3 = repo.find_by_session_paginated(sess.session_urn, limit=2, cursor=cursor2)
    assert len(p3) == 1
    assert p3[0].record_urn == sorted_records[4].record_urn
    
    # test active by worker pagination
    w_p1 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=3)
    assert len(w_p1) == 3


@pytest.mark.parametrize("adapter_class", [
    (InMemoryPostMortemRecordRepository, None),
    (FilePostMortemRecordRepository, "temp_storage")
])
def test_postmortem_pagination(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    sess = make_session()
    
    pms = [make_postmortem(sess.session_urn) for _ in range(3)]
    for pm in pms:
        repo.save(pm)
        
    sorted_pms = sorted(pms, key=lambda x: x.postmortem_urn)
    
    p1 = repo.find_by_session_paginated(sess.session_urn, limit=2)
    assert len(p1) == 2
    assert p1[0].postmortem_urn == sorted_pms[0].postmortem_urn
    
    cursor = p1[1].postmortem_urn
    p2 = repo.find_by_session_paginated(sess.session_urn, limit=2, cursor=cursor)
    assert len(p2) == 1
    assert p2[0].postmortem_urn == sorted_pms[2].postmortem_urn


# 5. LINEAGE TRAVERSAL

@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewRecordRepository, None),
    (FileReviewRecordRepository, "temp_storage")
])
def test_review_lineage_traversal(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
        
    sess = make_session()
    
    r1 = make_record(sess.session_urn, review_version=1)
    r1.is_active = False
    r1.superseded_by_version = 2
    repo.save(r1)
    
    r2 = make_record(
        sess.session_urn, 
        decision_id=r1.decision_id, 
        worker_urn=r1.worker_urn, 
        review_version=2
    )
    r2.is_active = True
    repo.save(r2)
    
    lineage = repo.find_review_lineage(r1.record_urn)
    assert len(lineage) == 2
    assert lineage[0].review_version == 1
    assert lineage[1].review_version == 2


@pytest.mark.parametrize("adapter_class", [
    (InMemoryReviewRecordRepository, None),
    (FileReviewRecordRepository, "temp_storage")
])
def test_record_occ(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
    sess = make_session()
    r = make_record(sess.session_urn)
    repo.save(r)
    
    # Valid update
    r.aggregate_version = 2
    repo.save(r)
    
    # Conflict
    r.aggregate_version = 1
    with pytest.raises(ConcurrencyConflictError):
        repo.save(r)


@pytest.mark.parametrize("adapter_class", [
    (InMemoryPostMortemRecordRepository, None),
    (FilePostMortemRecordRepository, "temp_storage")
])
def test_postmortem_occ(adapter_class, temp_storage, request):
    repo_cls, storage_fixture = adapter_class
    if storage_fixture:
        path = request.getfixturevalue(storage_fixture)
        repo = repo_cls(storage_dir=path)
    else:
        repo = repo_cls()
    sess = make_session()
    pm = make_postmortem(sess.session_urn)
    repo.save(pm)
    
    # Valid update
    pm.aggregate_version = 2
    repo.save(pm)
    
    # Conflict
    pm.aggregate_version = 1
    with pytest.raises(ConcurrencyConflictError):
        repo.save(pm)


def test_inmemory_not_found_urns():
    repo_s = InMemoryReviewSessionRepository()
    repo_r = InMemoryReviewRecordRepository()
    repo_pm = InMemoryPostMortemRecordRepository()
    assert repo_s.find_by_urn("urn:karsa:review:session:none") is None
    assert repo_r.find_by_urn("urn:karsa:review:record:none") is None
    assert repo_pm.find_by_urn("urn:karsa:postmortem:record:none") is None
    
    # Empty lineage walks
    assert repo_r.find_review_lineage("urn:karsa:review:record:none") == []
    assert repo_pm.find_postmortem_lineage("urn:karsa:postmortem:record:none") == []

    # Find existing
    sess = make_session()
    repo_s.save(sess)
    assert repo_s.find_by_urn(sess.session_urn) is not None

    record = make_record(sess.session_urn)
    repo_r.save(record)
    assert repo_r.find_by_urn(record.record_urn) is not None

    pm = make_postmortem(sess.session_urn)
    repo_pm.save(pm)
    assert repo_pm.find_by_urn(pm.postmortem_urn) is not None

    # Search non-matching in non-empty repo
    assert repo_s.find_by_urn("urn:karsa:review:session:different") is None
    assert repo_r.find_by_urn("urn:karsa:review:record:different") is None
    assert repo_pm.find_by_urn("urn:karsa:postmortem:record:different") is None


def test_file_not_found_urns(temp_storage):
    repo_s = FileReviewSessionRepository(storage_dir=temp_storage)
    repo_r = FileReviewRecordRepository(storage_dir=temp_storage)
    repo_pm = FilePostMortemRecordRepository(storage_dir=temp_storage)
    assert repo_s.find_by_urn("bad-urn-no-colon") is None
    assert repo_r.find_by_urn("bad-urn-no-colon") is None
    assert repo_pm.find_by_urn("bad-urn-no-colon") is None

    # Search non-matching in non-empty repo
    sess = make_session()
    repo_s.save(sess)
    assert repo_s.find_by_urn("urn:karsa:review:session:different") is None
    assert repo_s.find_by_urn("bad-urn-no-colon") is None

    r = make_record(sess.session_urn)
    repo_r.save(r)
    assert repo_r.find_by_urn("urn:karsa:review:record:different") is None
    assert repo_r.find_by_urn("bad-urn-no-colon") is None

    pm = make_postmortem(sess.session_urn)
    repo_pm.save(pm)
    assert repo_pm.find_by_urn("urn:karsa:postmortem:record:different") is None
    assert repo_pm.find_by_urn("bad-urn-no-colon") is None


def test_file_corrupt_files(temp_storage):
    records_dir = os.path.join(temp_storage, "records")
    os.makedirs(records_dir, exist_ok=True)
    with open(os.path.join(records_dir, "corrupt.json"), "w") as f:
        f.write("{corrupt:")
        
    pms_dir = os.path.join(temp_storage, "pms")
    os.makedirs(pms_dir, exist_ok=True)
    with open(os.path.join(pms_dir, "corrupt.json"), "w") as f:
        f.write("{corrupt:")
        
    # Write valid files too
    sess = make_session()
    r = make_record(sess.session_urn)
    with open(os.path.join(records_dir, f"{r.record_id}.json"), "w") as f:
        json.dump(r.to_dict(), f)

    pm = make_postmortem(sess.session_urn)
    with open(os.path.join(pms_dir, f"{pm.postmortem_id}.json"), "w") as f:
        json.dump(pm.to_dict(), f)
        
    repo_r = FileReviewRecordRepository(storage_dir=records_dir)
    loaded_recs = repo_r._load_all_records()
    assert len(loaded_recs) == 1
    assert loaded_recs[0].record_id == r.record_id
    
    repo_pm = FilePostMortemRecordRepository(storage_dir=pms_dir)
    loaded_pms = repo_pm._load_all_pms()
    assert len(loaded_pms) == 1
    assert loaded_pms[0].postmortem_id == pm.postmortem_id


def test_file_temp_write_failure(temp_storage):
    repo_s = FileReviewSessionRepository(storage_dir=temp_storage)
    repo_r = FileReviewRecordRepository(storage_dir=temp_storage)
    repo_pm = FilePostMortemRecordRepository(storage_dir=temp_storage)
    
    sess = make_session()
    r = make_record(sess.session_urn)
    pm = make_postmortem(sess.session_urn)
    
    import tempfile
    original_mkstemp = tempfile.mkstemp
    def fake_mkstemp(*args, **kwargs):
        raise OSError("Disk full")
    
    tempfile.mkstemp = fake_mkstemp
    try:
        with pytest.raises(OSError):
            repo_s.save(sess)
        with pytest.raises(OSError):
            repo_r.save(r)
        with pytest.raises(OSError):
            repo_pm.save(pm)
    finally:
        tempfile.mkstemp = original_mkstemp



def test_postmortem_lineage_traversal(temp_storage):
    repo_inmem = InMemoryPostMortemRecordRepository()
    repo_file = FilePostMortemRecordRepository(storage_dir=temp_storage)
    
    sess = make_session()
    pm1 = make_postmortem(sess.session_urn, postmortem_version=1)
    pm1.is_active = False
    pm1.superseded_by_version = 2
    
    pm2 = make_postmortem(sess.session_urn, decision_id=pm1.decision_id, postmortem_version=2)
    pm2.is_active = True
    
    for repo in (repo_inmem, repo_file):
        repo.save(pm1)
        repo.save(pm2)
        lineage = repo.find_postmortem_lineage(pm1.postmortem_urn)
        assert len(lineage) == 2
        assert lineage[0].postmortem_version == 1
        assert lineage[1].postmortem_version == 2


def test_inmemory_session_occ_success():
    repo = InMemoryReviewSessionRepository()
    sess = make_session()
    repo.save(sess)
    
    sess.aggregate_version = 2
    repo.save(sess)
    
    loaded = repo.find_by_id(sess.session_id)
    assert loaded.aggregate_version == 2


def test_inmemory_record_find_active_by_worker_filtering():
    repo = InMemoryReviewRecordRepository()
    sess = make_session()
    
    r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
    r1.is_active = True
    repo.save(r1)
    
    r2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
    r2.is_active = False
    repo.save(r2)
    
    r3 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w2")
    r3.is_active = True
    repo.save(r3)
    
    res = repo.find_active_by_worker("urn:karsa:worker:w1", limit=10)
    assert len(res) == 1
    assert res[0].record_id == r1.record_id


def test_inmemory_record_find_active_by_worker_pagination():
    repo = InMemoryReviewRecordRepository()
    sess = make_session()
    
    r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
    r2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
    
    sorted_recs = sorted([r1, r2], key=lambda x: x.record_urn)
    for r in sorted_recs:
        r.is_active = True
        repo.save(r)
        
    res1 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=None)
    assert len(res1) == 1
    assert res1[0].record_urn == sorted_recs[0].record_urn
    
    res2 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=sorted_recs[0].record_urn)
    assert len(res2) == 1
    assert res2[0].record_urn == sorted_recs[1].record_urn
    
    res3 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=sorted_recs[1].record_urn)
    assert len(res3) == 0


def test_inmemory_record_find_by_session_paginated_filtering():
    repo = InMemoryReviewRecordRepository()
    sess1 = make_session()
    sess2 = make_session()
    
    r1 = make_record(sess1.session_urn)
    r2 = make_record(sess2.session_urn)
    repo.save(r1)
    repo.save(r2)
    
    res = repo.find_by_session_paginated(sess1.session_urn, limit=10)
    assert len(res) == 1
    assert res[0].record_id == r1.record_id


def test_inmemory_postmortem_find_by_session_paginated_filtering():
    repo = InMemoryPostMortemRecordRepository()
    sess1 = make_session()
    sess2 = make_session()
    
    pm1 = make_postmortem(sess1.session_urn)
    pm2 = make_postmortem(sess2.session_urn)
    repo.save(pm1)
    repo.save(pm2)
    
    res = repo.find_by_session_paginated(sess1.session_urn, limit=10)
    assert len(res) == 1
    assert res[0].postmortem_id == pm1.postmortem_id


def test_file_occ_success(temp_storage):
    repo_s = FileReviewSessionRepository(storage_dir=temp_storage)
    repo_r = FileReviewRecordRepository(storage_dir=temp_storage)
    repo_pm = FilePostMortemRecordRepository(storage_dir=temp_storage)
    
    sess = make_session()
    repo_s.save(sess)
    sess.aggregate_version = 2
    repo_s.save(sess)
    
    r = make_record(sess.session_urn)
    repo_r.save(r)
    r.aggregate_version = 2
    repo_r.save(r)
    
    pm = make_postmortem(sess.session_urn)
    repo_pm.save(pm)
    pm.aggregate_version = 2
    repo_pm.save(pm)
    
    assert repo_s.find_by_id(sess.session_id).aggregate_version == 2
    assert repo_r.find_by_id(r.record_id).aggregate_version == 2
    assert repo_pm.find_by_id(pm.postmortem_id).aggregate_version == 2


def test_file_save_write_exception(temp_storage):
    repo_s = FileReviewSessionRepository(storage_dir=temp_storage)
    repo_r = FileReviewRecordRepository(storage_dir=temp_storage)
    repo_pm = FilePostMortemRecordRepository(storage_dir=temp_storage)
    
    sess = make_session()
    r = make_record(sess.session_urn)
    pm = make_postmortem(sess.session_urn)
    
    import unittest.mock as mock
    with mock.patch("json.dump", side_effect=TypeError("mocked serialize error")):
        with pytest.raises(TypeError):
            repo_s.save(sess)
        with pytest.raises(TypeError):
            repo_r.save(r)
        with pytest.raises(TypeError):
            repo_pm.save(pm)
            
    for filename in os.listdir(temp_storage):
        assert not filename.endswith(".tmp")


def test_file_find_by_urn_invalid_type(temp_storage):
    repo_s = FileReviewSessionRepository(storage_dir=temp_storage)
    repo_r = FileReviewRecordRepository(storage_dir=temp_storage)
    repo_pm = FilePostMortemRecordRepository(storage_dir=temp_storage)
    
    assert repo_s.find_by_urn(None) is None
    assert repo_r.find_by_urn(None) is None
    assert repo_pm.find_by_urn(None) is None
    
    assert repo_s.find_by_urn(123) is None
    assert repo_r.find_by_urn(123) is None
    assert repo_pm.find_by_urn(123) is None


def test_file_load_all_records_ignored_files(temp_storage):
    records_dir = os.path.join(temp_storage, "records")
    pms_dir = os.path.join(temp_storage, "pms")
    os.makedirs(records_dir, exist_ok=True)
    os.makedirs(pms_dir, exist_ok=True)
    
    sess = make_session()
    r = make_record(sess.session_urn)
    pm = make_postmortem(sess.session_urn)
    
    repo_r = FileReviewRecordRepository(storage_dir=records_dir)
    repo_pm = FilePostMortemRecordRepository(storage_dir=pms_dir)
    
    repo_r.save(r)
    repo_pm.save(pm)
    
    with open(os.path.join(records_dir, "temp.tmp"), "w") as f:
        f.write("ignored")
    with open(os.path.join(records_dir, "readme.txt"), "w") as f:
        f.write("ignored")
        
    with open(os.path.join(pms_dir, "temp.tmp"), "w") as f:
        f.write("ignored")
    with open(os.path.join(pms_dir, "readme.txt"), "w") as f:
        f.write("ignored")
        
    loaded_recs = repo_r._load_all_records()
    assert len(loaded_recs) == 1
    
    loaded_pms = repo_pm._load_all_pms()
    assert len(loaded_pms) == 1


def test_file_record_find_active_by_worker_pagination(temp_storage):
    repo = FileReviewRecordRepository(storage_dir=temp_storage)
    sess = make_session()
    
    r1 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
    r2 = make_record(sess.session_urn, worker_urn="urn:karsa:worker:w1")
    
    sorted_recs = sorted([r1, r2], key=lambda x: x.record_urn)
    for r in sorted_recs:
        r.is_active = True
        repo.save(r)
        
    res1 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=None)
    assert len(res1) == 1
    assert res1[0].record_urn == sorted_recs[0].record_urn
    
    res2 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=sorted_recs[0].record_urn)
    assert len(res2) == 1
    assert res2[0].record_urn == sorted_recs[1].record_urn
    
    res3 = repo.find_active_by_worker("urn:karsa:worker:w1", limit=1, cursor=sorted_recs[1].record_urn)
    assert len(res3) == 0



