import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
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
from karsa.allocation.domain.events import (
    AllocationCalculatedEvent,
    AllocationSupersededEvent,
    AllocationInvalidatedEvent
)
from karsa.allocation.infrastructure.storage.in_memory_repositories import (
    InMemoryAllocationSessionRepository,
    InMemoryAllocationDecisionRecordRepository,
    ConcurrencyConflictError
)
from karsa.allocation.application.service.allocation_services import (
    AllocationCalculationService,
    RankingProjectionService,
    AllocationReplayService,
    AllocationInvalidationService,
    MethodologyDriftException,
    ReplayIntegrityException
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
        attribution_score=1.05,
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

def test_calculation_service_success_and_supersede():
    sess_repo = InMemoryAllocationSessionRepository()
    rec_repo = InMemoryAllocationDecisionRecordRepository()
    events = []
    calc_service = AllocationCalculationService(rec_repo, sess_repo, events)
    
    sess_id = str(uuid.uuid4())
    session = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="key"
    )
    session.start() # Move status to CALCULATING
    sess_repo.save(session)
    
    # Insert a record with a different decision_id for the same worker
    rec_diff = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()),
        record_urn=f"urn:karsa:allocation:record:{uuid.uuid4()}",
        session_urn=session.session_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-diff", # different decision_id
        horizon=make_horizon(),
        allocation_score=make_score(),
        recommendation=make_recommendation(),
        allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
        allocation_policy_hash="a" * 64,
        allocation_strategy_version="v1.0",
        allocation_manifest_hash=make_manifest().compute_hash()
    )
    rec_repo.save(rec_diff)
    
    # Run calculation first time (no supersede)
    record = calc_service.calculate_allocations(
        session_urn=session.session_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        raw_score=0.8,
        brier_score=0.15,
        selection_return=0.05,
        review_score=0.9,
        has_warning=False,
        allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
        allocation_policy_hash="a" * 64,
        allocation_strategy_version="v1.0"
    )
    
    assert record.is_active is True
    assert record.allocation_version == 1
    assert record.supersedes_record_urn is None
    
    # Verify events published: 1 AllocationCalculatedEvent
    assert len(events) == 1
    assert isinstance(events[0], AllocationCalculatedEvent)
    assert events[0].recommended_weight == record.recommendation.recommended_weight
    
    # Run calculation second time for same worker/decision -> should supersede the first
    record2 = calc_service.calculate_allocations(
        session_urn=session.session_urn,
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        raw_score=0.85,
        brier_score=0.10,
        selection_return=0.08,
        review_score=0.95,
        has_warning=True, # applying warning penalty (0.5)
        allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
        allocation_policy_hash="a" * 64,
        allocation_strategy_version="v1.0"
    )
    
    assert record2.is_active is True
    assert record2.allocation_version == 2
    assert record2.supersedes_record_urn == record.record_urn
    
    # Verify the first record was updated to inactive
    old_record = rec_repo.find_by_urn(record.record_urn)
    assert old_record.is_active is False
    assert old_record.superseded_by_version == 2
    
    # Verify events published: 1 AllocationSupersededEvent and 1 AllocationCalculatedEvent
    assert len(events) == 3
    assert isinstance(events[1], AllocationSupersededEvent)
    assert isinstance(events[2], AllocationCalculatedEvent)

def test_calculation_service_validation_failures():
    sess_repo = InMemoryAllocationSessionRepository()
    rec_repo = InMemoryAllocationDecisionRecordRepository()
    calc_service = AllocationCalculationService(rec_repo, sess_repo)
    
    # 1. Session not found
    with pytest.raises(ValueError, match="AllocationSession not found"):
        calc_service.calculate_allocations(
            session_urn="urn:karsa:allocation:session:missing",
            worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1",
            raw_score=0.8,
            brier_score=0.1,
            selection_return=0.0,
            review_score=1.0,
            has_warning=False,
            allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
            allocation_policy_hash="a" * 64,
            allocation_strategy_version="v1.0"
        )
        
    # 2. Session not in CALCULATING state
    sess_id = str(uuid.uuid4())
    session = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="key"
    )
    sess_repo.save(session) # status is INITIATED
    
    with pytest.raises(ValueError, match="is not in CALCULATING status"):
        calc_service.calculate_allocations(
            session_urn=session.session_urn,
            worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1",
            raw_score=0.8,
            brier_score=0.1,
            selection_return=0.0,
            review_score=1.0,
            has_warning=False,
            allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
            allocation_policy_hash="a" * 64,
            allocation_strategy_version="v1.0"
        )

def test_calculation_service_occ_retries():
    sess_repo = InMemoryAllocationSessionRepository()
    rec_repo = InMemoryAllocationDecisionRecordRepository()
    calc_service = AllocationCalculationService(rec_repo, sess_repo)
    
    sess_id = str(uuid.uuid4())
    session = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="key"
    )
    session.start()
    sess_repo.save(session)
    
    # Mock save to raise OCC conflict twice then succeed
    call_count = 0
    orig_save = rec_repo.save
    def mock_save(record):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConcurrencyConflictError("OCC conflict")
        return orig_save(record)
        
    with patch.object(rec_repo, "save", side_effect=mock_save):
        record = calc_service.calculate_allocations(
            session_urn=session.session_urn,
            worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1",
            raw_score=0.8,
            brier_score=0.1,
            selection_return=0.05,
            review_score=1.0,
            has_warning=False,
            allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
            allocation_policy_hash="a" * 64,
            allocation_strategy_version="v1.0"
        )
        assert record is not None
        assert call_count == 3

    # Mock save to fail all 3 times
    call_count = 0
    def mock_save_fail(record):
        nonlocal call_count
        call_count += 1
        raise ConcurrencyConflictError("OCC conflict")
        
    with patch.object(rec_repo, "save", side_effect=mock_save_fail):
        with pytest.raises(ConcurrencyConflictError):
            calc_service.calculate_allocations(
                session_urn=session.session_urn,
                worker_urn="urn:karsa:worker:w1",
                decision_id="dec-1",
                raw_score=0.8,
                brier_score=0.1,
                selection_return=0.05,
                review_score=1.0,
                has_warning=False,
                allocation_methodology_urn="urn:karsa:allocation:methodology:m1",
                allocation_policy_hash="a" * 64,
                allocation_strategy_version="v1.0"
            )
        assert call_count == 3

def test_ranking_projection_deterministic_ordering():
    proj_service = RankingProjectionService()
    horizon = make_horizon()
    sess_urn = "urn:karsa:allocation:session:s1"
    m = make_manifest()
    
    # 5 factors sorting resolution test:
    # 1. allocation score (Descending)
    # 2. brier score (Ascending)
    # 3. selection return (Descending)
    # 4. review score (Descending)
    # 5. worker_urn alphabetical (Ascending)
    
    brier_scores = {
        "urn:karsa:worker:w1": 0.2,
        "urn:karsa:worker:w2": 0.2,
        "urn:karsa:worker:w3": 0.2,
        "urn:karsa:worker:w4": 0.2,
        "urn:karsa:worker:w5": 0.25,
        "urn:karsa:worker:w6": 0.1
    }
    
    selection_returns = {
        "urn:karsa:worker:w1": 0.1,
        "urn:karsa:worker:w2": 0.1,
        "urn:karsa:worker:w3": 0.1,
        "urn:karsa:worker:w4": 0.05,
        "urn:karsa:worker:w5": 0.1,
        "urn:karsa:worker:w6": 0.2
    }
    
    review_scores = {
        "urn:karsa:worker:w1": 0.9,
        "urn:karsa:worker:w2": 0.9,
        "urn:karsa:worker:w3": 0.8,
        "urn:karsa:worker:w4": 0.9,
        "urn:karsa:worker:w5": 0.9,
        "urn:karsa:worker:w6": 0.9
    }
    
    # Create records
    records = []
    
    # Record 6: raw score = 0.75 (lowest raw score, so it should rank last despite good Brier/return)
    r6 = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r6",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:w6", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.75, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )
    
    # Record 5: raw score = 0.8, Brier = 0.25 (higher Brier than 4, so it should rank below 4)
    r5 = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r5",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:w5", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )
    
    # Record 4: raw score = 0.8, Brier = 0.2, selection return = 0.05 (lower return than 3, rank below 3)
    r4 = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r4",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:w4", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )

    # Record 3: raw score = 0.8, Brier = 0.2, return = 0.1, review score = 0.8 (lower review than 2, rank below 2)
    r3 = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r3",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:w3", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )

    # Record 2: raw score = 0.8, Brier = 0.2, return = 0.1, review = 0.9, w2 (w1 is alphabetically earlier, so rank below 1)
    r2 = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r2",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:w2", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )

    # Record 1: raw score = 0.8, Brier = 0.2, return = 0.1, review = 0.9, w1 (winner)
    r1 = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:r1",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:w1", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )

    r_inactive = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:rinactive",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:winactive", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash(),
        is_active=False
    )
    r_diff_session = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:rdiffsession",
        session_urn="urn:karsa:allocation:session:other", worker_urn="urn:karsa:worker:wdiffsession", decision_id="dec-1",
        horizon=horizon, allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )
    r_diff_horizon = AllocationDecisionRecord(
        record_id=str(uuid.uuid4()), record_urn="urn:karsa:allocation:record:rdiffhorizon",
        session_urn=sess_urn, worker_urn="urn:karsa:worker:wdiffhorizon", decision_id="dec-1",
        horizon=make_horizon(horizon_id="180D"), allocation_score=AllocationScore(0.8, 1.0, 1.0, 1.0),
        recommendation=make_recommendation(), allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash, allocation_strategy_version=m.allocation_strategy_version,
        allocation_manifest_hash=m.compute_hash()
    )

    records = [r6, r5, r4, r3, r2, r1, r_inactive, r_diff_session, r_diff_horizon]
    
    # Generate ranking
    projection = proj_service.build_ranking_projection(
        session_urn=sess_urn,
        horizon=horizon,
        records=records,
        brier_scores=brier_scores,
        selection_returns=selection_returns,
        review_scores=review_scores
    )
    
    # Assert correct order
    assert len(projection.rankings) == 6
    assert projection.rankings[0].worker_urn == "urn:karsa:worker:w1"
    assert projection.rankings[0].rank_index == 1
    
    assert projection.rankings[1].worker_urn == "urn:karsa:worker:w2"
    assert projection.rankings[2].worker_urn == "urn:karsa:worker:w3"
    assert projection.rankings[3].worker_urn == "urn:karsa:worker:w4"
    assert projection.rankings[4].worker_urn == "urn:karsa:worker:w5"
    assert projection.rankings[5].worker_urn == "urn:karsa:worker:w6"

def test_replay_service_success_and_failures():
    rec_repo = InMemoryAllocationDecisionRecordRepository()
    replay_service = AllocationReplayService(rec_repo)
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
    
    # 1. Replay Success
    assert replay_service.verify_replay(record.record_urn, m) is True
    
    # 2. Record not found
    with pytest.raises(ValueError, match="AllocationDecisionRecord not found"):
        replay_service.verify_replay("urn:karsa:allocation:record:missing", m)
        
    # 3. Methodology drift: URN mismatch
    m_drift_urn = AllocationMethodologyManifest(
        allocation_methodology_urn="urn:karsa:allocation:methodology:m2", # drifted
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version=m.allocation_strategy_version
    )
    with pytest.raises(MethodologyDriftException, match="Methodology URN drift detected"):
        replay_service.verify_replay(record.record_urn, m_drift_urn)

    # 4. Methodology drift: policy hash mismatch
    m_drift_policy = AllocationMethodologyManifest(
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash="b" * 64, # drifted
        allocation_strategy_version=m.allocation_strategy_version
    )
    with pytest.raises(MethodologyDriftException, match="Policy hash drift detected"):
        replay_service.verify_replay(record.record_urn, m_drift_policy)

    # 5. Methodology drift: strategy version mismatch
    m_drift_version = AllocationMethodologyManifest(
        allocation_methodology_urn=m.allocation_methodology_urn,
        allocation_policy_hash=m.allocation_policy_hash,
        allocation_strategy_version="v2.0" # drifted
    )
    with pytest.raises(MethodologyDriftException, match="Strategy version drift detected"):
        replay_service.verify_replay(record.record_urn, m_drift_version)

    # 6. Replay Integrity Exception (manifest hash mismatch)
    m_corrupted = AllocationMethodologyManifest(
        allocation_methodology_urn=record.allocation_methodology_urn,
        allocation_policy_hash=record.allocation_policy_hash,
        allocation_strategy_version=record.allocation_strategy_version
    )
    orig_compute_hash = AllocationMethodologyManifest.compute_hash
    def mock_compute_hash(self):
        if self is m_corrupted:
            return "invalid_hash"
        return orig_compute_hash(self)

    with patch("karsa.allocation.domain.value_objects.AllocationMethodologyManifest.compute_hash", new=mock_compute_hash):
        with pytest.raises(ReplayIntegrityException, match="Replay manifest hash mismatch"):
            replay_service.verify_replay(record.record_urn, m_corrupted)

def test_invalidation_service():
    rec_repo = InMemoryAllocationDecisionRecordRepository()
    events = []
    invalidation_service = AllocationInvalidationService(rec_repo, events)
    sess_urn = "urn:karsa:allocation:session:s1"
    m = make_manifest()
    
    # Create lineage chain r1 -> r2
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
    
    rec_repo.save(r1)
    rec_repo.save(r2)
    
    # Invalidate starting from r2
    invalidated_records = invalidation_service.invalidate_lineage(
        start_record_urn=r2.record_urn,
        invalidating_version=5
    )
    
    # Verify r2 was invalidated
    assert len(invalidated_records) == 1
    assert invalidated_records[0].record_urn == r2.record_urn
    assert invalidated_records[0].is_active is False
    assert invalidated_records[0].invalidated_by_version == 5
    
    # Verify event published: 1 AllocationInvalidatedEvent
    assert len(events) == 1
    assert isinstance(events[0], AllocationInvalidatedEvent)
    assert events[0].record_urn == r2.record_urn
    assert events[0].invalidated_by_version == 5
