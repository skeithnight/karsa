import pytest
import shutil
import os
from karsa.thesis.domain.models import (
    Thesis, ThesisSnapshot, ThesisTransition, ThesisDelta,
    ThesisAssumptionIdentity, ThesisAssumptionVersion
)
from karsa.thesis.domain.value_objects import LifecycleState, AssumptionLifecycleState
from karsa.thesis.domain.repository.repositories import (
    ConcurrencyDriftError, ImmutableMutationError, LineageCycleError
)
from karsa.thesis.infrastructure.storage.memory_repo import (
    InMemoryThesisRepository, InMemoryThesisSnapshotRepository, InMemoryThesisTransitionRepository,
    InMemoryAssumptionIdentityRepository, InMemoryAssumptionVersionRepository
)
from karsa.thesis.infrastructure.storage.file_repo import (
    FileThesisRepository, FileThesisSnapshotRepository, FileThesisTransitionRepository,
    FileAssumptionIdentityRepository, FileAssumptionVersionRepository
)

def test_thesis_repo_memory_occ():
    repo = InMemoryThesisRepository()
    t1 = Thesis("urn1", "snap1", LifecycleState.PROPOSED, 1)
    repo.save(t1)
    
    # Successful update
    t2 = Thesis("urn1", "snap2", LifecycleState.ACTIVE, 2)
    repo.save(t2)
    
    # OCC conflict
    t3 = Thesis("urn1", "snap3", LifecycleState.REFINING, 2) # version should be 3
    with pytest.raises(ConcurrencyDriftError):
        repo.save(t3)
        
    # Test active list
    res = repo.list_active(limit=10)
    assert len(res) == 1
    assert res[0].thesis_urn == "urn1"

def test_thesis_repo_pagination():
    repo = InMemoryThesisRepository()
    for i in range(1, 6):
        t = Thesis(f"urn{i}", "snap1", LifecycleState.ACTIVE, 1)
        repo.save(t)
    
    # Keyset pagination
    page1 = repo.list_active(limit=2)
    assert len(page1) == 2
    assert page1[0].thesis_urn == "urn1"
    assert page1[1].thesis_urn == "urn2"
    
    page2 = repo.list_active(limit=2, last_urn="urn2")
    assert len(page2) == 2
    assert page2[0].thesis_urn == "urn3"
    assert page2[1].thesis_urn == "urn4"

def test_snapshot_repo_immutability_and_lineage():
    repo = InMemoryThesisSnapshotRepository()
    s1 = ThesisSnapshot("snap1", 1, LifecycleState.ACTIVE, "reg1", None, None, [])
    s2 = ThesisSnapshot("snap2", 2, LifecycleState.REFINING, "reg1", "snap1", None, [])
    s3 = ThesisSnapshot("snap3", 3, LifecycleState.ACTIVE, "reg1", "snap2", None, [])
    s_cycle = ThesisSnapshot("snap4", 4, LifecycleState.ACTIVE, "reg1", "snap4", None, []) # self reference
    
    repo.save(s1)
    repo.save(s2)
    repo.save(s3)
    repo.save(s_cycle)
    
    with pytest.raises(ImmutableMutationError):
        repo.save(s1)
        
    lineage = repo.fetch_snapshot_lineage("snap3")
    assert len(lineage) == 3
    assert lineage[0].snapshot_urn == "snap3"
    assert lineage[1].snapshot_urn == "snap2"
    assert lineage[2].snapshot_urn == "snap1"
    
    with pytest.raises(LineageCycleError):
        repo.fetch_snapshot_lineage("snap4")

def test_transition_repo():
    repo = InMemoryThesisTransitionRepository()
    delta = ThesisDelta("d1", "h1", [], [])
    t1 = ThesisTransition("trans1", None, None, delta)
    t2 = ThesisTransition("trans2", "trans1", None, delta)
    repo.save(t1)
    repo.save(t2)
    
    with pytest.raises(ImmutableMutationError):
        repo.save(t1)
        
    lineage = repo.fetch_transition_lineage("trans2")
    assert len(lineage) == 2

def test_assumption_repos():
    id_repo = InMemoryAssumptionIdentityRepository()
    ver_repo = InMemoryAssumptionVersionRepository()
    
    i1 = ThesisAssumptionIdentity("a1")
    id_repo.save(i1)
    assert id_repo.get_by_urn("a1").assumption_urn == "a1"
    
    v1 = ThesisAssumptionVersion("a1", 1, "stmnt", 0.9, AssumptionLifecycleState.ACTIVE, "h1")
    ver_repo.save(v1)
    assert ver_repo.get_by_urn_and_version("a1", 1).assumption_manifest_hash == "h1"
    
    with pytest.raises(ImmutableMutationError):
        ver_repo.save(v1)

def test_file_repos():
    d = "/tmp/karsa_test_repos"
    if os.path.exists(d):
        shutil.rmtree(d)
        
    t_repo = FileThesisRepository(os.path.join(d, "theses"))
    t1 = Thesis("urn1", "snap1", LifecycleState.ACTIVE, 1)
    t_repo.save(t1)
    assert os.path.exists(os.path.join(d, "theses", "urn1.json"))
    
    s_repo = FileThesisSnapshotRepository(os.path.join(d, "snapshots"))
    s1 = ThesisSnapshot("snap1", 1, LifecycleState.ACTIVE, "reg1", None, None, [])
    s_repo.save(s1)
    assert os.path.exists(os.path.join(d, "snapshots", "snap1.json"))
    
    tr_repo = FileThesisTransitionRepository(os.path.join(d, "transitions"))
    tr_repo.save(ThesisTransition("tr1", None, None, ThesisDelta("d1", "h1", [], [])))
    
    ai_repo = FileAssumptionIdentityRepository(os.path.join(d, "assumption_identities"))
    ai_repo.save(ThesisAssumptionIdentity("a1"))
    
    av_repo = FileAssumptionVersionRepository(os.path.join(d, "assumption_versions"))
    av_repo.save(ThesisAssumptionVersion("a1", 1, "stmnt", 0.9, AssumptionLifecycleState.ACTIVE, "h1"))

def test_missing_coverage():
    t_repo = InMemoryThesisRepository()
    t_repo.save(Thesis("u1", "s1", LifecycleState.ACTIVE, 1))
    assert t_repo.get_by_urn("u1") is not None
    assert t_repo.get_by_urn("missing") is None
    
    s_repo = InMemoryThesisSnapshotRepository()
    s_repo.save(ThesisSnapshot("s1", 1, LifecycleState.ACTIVE, "reg1", None, None, []))
    assert s_repo.get_by_urn("s1") is not None
    assert s_repo.get_by_urn("missing") is None
    
    tr_repo = InMemoryThesisTransitionRepository()
    tr_repo.save(ThesisTransition("tr1", None, None, ThesisDelta("d1", "h1", [], [])))
    assert tr_repo.get_by_urn("tr1") is not None
    assert tr_repo.get_by_urn("missing") is None

    av_repo = InMemoryAssumptionVersionRepository()
    av_repo.save(ThesisAssumptionVersion("a1", 1, "stmnt", 0.9, AssumptionLifecycleState.ACTIVE, "h1"))
    assert av_repo.get_by_urn_and_version("a1", 1) is not None
    assert av_repo.get_by_urn_and_version("missing", 1) is None

def test_missing_coverage_more():
    repo1 = InMemoryThesisSnapshotRepository()
    repo1.get_by_urn("test")
    
    repo2 = InMemoryThesisTransitionRepository()
    repo2.get_by_urn("test")
    
    repo3 = InMemoryAssumptionIdentityRepository()
    repo3.get_by_urn("test")
    
    repo4 = InMemoryAssumptionVersionRepository()
    repo4.get_by_urn_and_version("test", 1)
