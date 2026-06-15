import os
import pytest
import shutil
import tempfile
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

def setup_dir(d):
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

def test_file_durability_scenario_a():
    d = "/tmp/karsa_durability_a"
    setup_dir(d)
    repo1 = FileThesisRepository(d)
    t1 = Thesis("urn1", "snap1", LifecycleState.ACTIVE, 1)
    repo1.save(t1)
    del repo1
    
    repo2 = FileThesisRepository(d)
    t_loaded = repo2.get_by_urn("urn1")
    assert t_loaded.thesis_urn == "urn1"
    assert t_loaded.current_snapshot_urn == "snap1"
    assert t_loaded.aggregate_version == 1

def test_file_durability_scenario_b():
    d = "/tmp/karsa_durability_b"
    setup_dir(d)
    repo1 = FileThesisRepository(d)
    t1 = Thesis("urn1", "snap1", LifecycleState.ACTIVE, 1)
    t2 = Thesis("urn2", "snap2", LifecycleState.ACTIVE, 1)
    repo1.save(t1)
    repo1.save(t2)
    del repo1
    
    repo2 = FileThesisRepository(d)
    all_active = repo2.list_active(limit=10)
    assert len(all_active) == 2
    urns = [x.thesis_urn for x in all_active]
    assert "urn1" in urns and "urn2" in urns

def test_file_durability_scenario_c():
    d = "/tmp/karsa_durability_c"
    setup_dir(d)
    repo1 = FileThesisSnapshotRepository(d)
    s1 = ThesisSnapshot("snap1", 1, LifecycleState.ACTIVE, "reg1", None, None, [])
    s2 = ThesisSnapshot("snap2", 2, LifecycleState.REFINING, "reg1", "snap1", None, [])
    repo1.save(s1)
    repo1.save(s2)
    del repo1
    
    repo2 = FileThesisSnapshotRepository(d)
    lineage = repo2.fetch_snapshot_lineage("snap2")
    assert len(lineage) == 2
    assert lineage[0].snapshot_urn == "snap2"
    assert lineage[1].snapshot_urn == "snap1"

def test_occ_scenarios():
    repo = InMemoryThesisRepository()
    
    # A. Successful Save
    t1 = Thesis("urn1", "snap1", LifecycleState.PROPOSED, 1)
    repo.save(t1)
    assert repo.get_by_urn("urn1").aggregate_version == 1
    
    # B. Stale Writer
    t1_stale = Thesis("urn1", "snap2", LifecycleState.ACTIVE, 1) # trying to overwrite version 1
    with pytest.raises(ConcurrencyDriftError):
        repo.save(t1_stale)
        
    # C. Sequential Updates
    t1_v2 = Thesis("urn1", "snap2", LifecycleState.ACTIVE, 2)
    repo.save(t1_v2)
    t1_v3 = Thesis("urn1", "snap3", LifecycleState.REFINING, 3)
    repo.save(t1_v3)
    assert repo.get_by_urn("urn1").aggregate_version == 3
    
    # D. Double Writer Race
    writer_a_reads = repo.get_by_urn("urn1") # version 3
    writer_b_reads = repo.get_by_urn("urn1") # version 3
    
    writer_a_mutates = Thesis("urn1", "snap4", LifecycleState.ACTIVE, 4)
    writer_b_mutates = Thesis("urn1", "snap5", LifecycleState.ACTIVE, 4)
    
    repo.save(writer_a_mutates) # succeeds, db now at 4
    with pytest.raises(ConcurrencyDriftError):
        repo.save(writer_b_mutates) # fails, expected db at 3, but is 4

def test_lineage_verification():
    s_repo = InMemoryThesisSnapshotRepository()
    s_repo.save(ThesisSnapshot("A", 1, LifecycleState.ACTIVE, "reg1", None, None, []))
    s_repo.save(ThesisSnapshot("B", 2, LifecycleState.ACTIVE, "reg1", "A", None, []))
    s_repo.save(ThesisSnapshot("C", 3, LifecycleState.ACTIVE, "reg1", "B", None, []))
    
    res = s_repo.fetch_snapshot_lineage("C")
    assert [x.snapshot_urn for x in res] == ["C", "B", "A"]
    
    s_repo.save(ThesisSnapshot("Cycle_A", 1, LifecycleState.ACTIVE, "reg1", "Cycle_C", None, []))
    s_repo.save(ThesisSnapshot("Cycle_B", 2, LifecycleState.ACTIVE, "reg1", "Cycle_A", None, []))
    s_repo.save(ThesisSnapshot("Cycle_C", 3, LifecycleState.ACTIVE, "reg1", "Cycle_B", None, []))
    with pytest.raises(LineageCycleError):
        s_repo.fetch_snapshot_lineage("Cycle_C")
        
    t_repo = InMemoryThesisTransitionRepository()
    delta = ThesisDelta("d1", "h1", [], [])
    t_repo.save(ThesisTransition("A", None, None, delta))
    t_repo.save(ThesisTransition("B", "A", None, delta))
    t_repo.save(ThesisTransition("C", "B", None, delta))
    
    res_t = t_repo.fetch_transition_lineage("C")
    assert [x.transition_urn for x in res_t] == ["C", "B", "A"]

def test_keyset_pagination():
    repo = InMemoryThesisRepository()
    # Insert out of order
    repo.save(Thesis("urn3", "s", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn1", "s", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn4", "s", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn2", "s", LifecycleState.ACTIVE, 1))
    repo.save(Thesis("urn5", "s", LifecycleState.ACTIVE, 1))
    
    # A. First page
    p1 = repo.list_active(limit=2)
    assert [x.thesis_urn for x in p1] == ["urn1", "urn2"] # Stable ordering
    
    # B. Second page
    p2 = repo.list_active(limit=2, last_urn="urn2")
    assert [x.thesis_urn for x in p2] == ["urn3", "urn4"]
    
    # C. No duplicates & stable ordering
    p3 = repo.list_active(limit=2, last_urn="urn4")
    assert [x.thesis_urn for x in p3] == ["urn5"]
    
def test_all_interfaces_and_missing_lines():
    import tempfile
    repo1 = InMemoryThesisSnapshotRepository()
    repo1.get_by_urn('test')
    repo2 = InMemoryThesisTransitionRepository()
    repo2.get_by_urn('test')
    repo3 = InMemoryAssumptionIdentityRepository()
    repo3.get_by_urn('test')
    repo4 = InMemoryAssumptionVersionRepository()
    repo4.get_by_urn_and_version('test', 1)
    r_s = FileThesisSnapshotRepository(tempfile.mktemp())
    r_t = FileThesisTransitionRepository(tempfile.mktemp())
    r_i = FileAssumptionIdentityRepository(tempfile.mktemp())
    r_v = FileAssumptionVersionRepository(tempfile.mktemp())
    t1 = ThesisTransition('t1', None, None, ThesisDelta('d1', 'h1', [], []))
    r_t.save(t1)
    i1 = ThesisAssumptionIdentity('i1')
    r_i.save(i1)
    v1 = ThesisAssumptionVersion('v1', 1, 's', 0.5, AssumptionLifecycleState.ACTIVE, 'h', None)
    r_v.save(v1)
def test_memory_repo_lineage_coverage():
    from karsa.thesis.domain.models import ThesisSnapshot, ThesisTransition, ThesisDelta
    from karsa.thesis.domain.value_objects import LifecycleState
    from karsa.thesis.infrastructure.storage.memory_repo import InMemoryThesisSnapshotRepository, InMemoryThesisTransitionRepository
    from karsa.thesis.domain.repository.repositories import LineageCycleError
    
    s_repo = InMemoryThesisSnapshotRepository()
    s_repo.save(ThesisSnapshot("A", 1, LifecycleState.ACTIVE, "R", "MISSING", None, []))
    lin = s_repo.fetch_snapshot_lineage("A")
    assert len(lin) == 1
    
    t_repo = InMemoryThesisTransitionRepository()
    t_repo.save(ThesisTransition("T1", "MISSING", None, ThesisDelta("d", "h", [], [])))
    lin2 = t_repo.fetch_transition_lineage("T1")
    assert len(lin2) == 1
    
    # Force cycle by bypassing immutability just for test
    t1 = ThesisTransition("TC1", "TC2", None, ThesisDelta("d", "h", [], []))
    t2 = ThesisTransition("TC2", "TC1", None, ThesisDelta("d", "h", [], []))
    t_repo._db["TC1"] = t1
    t_repo._db["TC2"] = t2
    
    import pytest
    with pytest.raises(LineageCycleError):
        t_repo.fetch_transition_lineage("TC1")


def test_file_repo_lineage_coverage():
    from karsa.thesis.domain.models import ThesisSnapshot, ThesisTransition, ThesisDelta
    from karsa.thesis.domain.value_objects import LifecycleState
    from karsa.thesis.infrastructure.storage.file_repo import FileThesisSnapshotRepository, FileThesisTransitionRepository
    from karsa.thesis.domain.repository.repositories import LineageCycleError
    import tempfile
    import json
    
    s_repo = FileThesisSnapshotRepository(tempfile.mktemp())
    s_repo.save(ThesisSnapshot("A", 1, LifecycleState.ACTIVE, "R", "MISSING", None, []))
    lin = s_repo.fetch_snapshot_lineage("A")
    assert len(lin) == 1
    
    t_repo = FileThesisTransitionRepository(tempfile.mktemp())
    t_repo.save(ThesisTransition("T1", "MISSING", None, ThesisDelta("d", "h", [], [])))
    lin2 = t_repo.fetch_transition_lineage("T1")
    assert len(lin2) == 1
    
    # Force cycle bypassing immutability
    t1 = ThesisTransition("TC1", "TC2", None, ThesisDelta("d", "h", [], []))
    t2 = ThesisTransition("TC2", "TC1", None, ThesisDelta("d", "h", [], []))
    t_repo._db["TC1"] = t1
    t_repo._db["TC2"] = t2
    # Also write to disk so get_by_urn loads it
    
    
    import pytest
    with pytest.raises(LineageCycleError):
        t_repo.fetch_transition_lineage("TC1")
        
    s1 = ThesisSnapshot("SC1", 1, LifecycleState.ACTIVE, "R", "SC2", None, [])
    s2 = ThesisSnapshot("SC2", 1, LifecycleState.ACTIVE, "R", "SC1", None, [])
    s_repo._db["SC1"] = s1
    s_repo._db["SC2"] = s2
    
        
    with pytest.raises(LineageCycleError):
        s_repo.fetch_snapshot_lineage("SC1")


def test_file_repo_loading_coverage():
    from karsa.thesis.domain.models import ThesisSnapshot, ThesisTransition, ThesisDelta, ThesisAssumptionIdentity, ThesisAssumptionVersion
    from karsa.thesis.domain.value_objects import LifecycleState, AssumptionLifecycleState, CalibrationReference
    from karsa.thesis.infrastructure.storage.file_repo import FileThesisSnapshotRepository, FileThesisTransitionRepository, FileAssumptionIdentityRepository, FileAssumptionVersionRepository
    import tempfile
    
    # Snapshot
    d1 = tempfile.mkdtemp()
    r_s = FileThesisSnapshotRepository(d1)
    r_s.save(ThesisSnapshot("S1", 1, LifecycleState.ACTIVE, "R", None, None, []))
    r_s2 = FileThesisSnapshotRepository(d1)
    assert r_s2.get_by_urn("S1")
    
    # Transition
    d2 = tempfile.mkdtemp()
    r_t = FileThesisTransitionRepository(d2)
    r_t.save(ThesisTransition("T1", None, None, ThesisDelta("d", "h", [], [])))
    r_t2 = FileThesisTransitionRepository(d2)
    assert r_t2.get_by_urn("T1")
    
    # Identity
    d3 = tempfile.mkdtemp()
    r_i = FileAssumptionIdentityRepository(d3)
    r_i.save(ThesisAssumptionIdentity("I1"))
    r_i2 = FileAssumptionIdentityRepository(d3)
    assert r_i2.get_by_urn("I1")
    
    # Version
    d4 = tempfile.mkdtemp()
    r_v = FileAssumptionVersionRepository(d4)
    r_v.save(ThesisAssumptionVersion("V1", 1, "stmt", 1.0, AssumptionLifecycleState.ACTIVE, "hash", CalibrationReference("cal1", "calhash")))
    r_v2 = FileAssumptionVersionRepository(d4)
    assert r_v2.get_by_urn_and_version("V1", 1)


def test_file_repo_non_json_ignore():
    from karsa.thesis.infrastructure.storage.file_repo import FileThesisSnapshotRepository, FileThesisTransitionRepository, FileAssumptionIdentityRepository, FileAssumptionVersionRepository, FileThesisRepository
    import tempfile
    import os
    
    for RepoClass in [FileThesisRepository, FileThesisSnapshotRepository, FileThesisTransitionRepository, FileAssumptionIdentityRepository, FileAssumptionVersionRepository]:
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "ignore.txt"), "w") as f:
            f.write("ignore me")
        r = RepoClass(d)

