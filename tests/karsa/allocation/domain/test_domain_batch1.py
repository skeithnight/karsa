import pytest
import uuid
from datetime import datetime, timezone
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
    StateTransitionError,
    ImmutabilityViolationError
)
from karsa.allocation.domain.events import (
    AllocationCalculatedEvent,
    AllocationSupersededEvent,
    AllocationInvalidatedEvent
)
from karsa.allocation.domain.lineage import reconstruct_allocation_lineage

# Helper fixtures / constructors
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


# 1. VALUE OBJECTS TESTS
def test_portfolio_horizon():
    h = make_horizon()
    assert h.horizon_id == "90D"
    
    # Validation
    with pytest.raises(ValueError, match="horizon_id must be a non-empty string"):
        PortfolioHorizon("", datetime.now(), datetime.now())
    with pytest.raises(ValueError, match="horizon_start and horizon_end must be datetime objects"):
        PortfolioHorizon("30D", "invalid", datetime.now())
    with pytest.raises(ValueError, match="horizon_start must be strictly before horizon_end"):
        PortfolioHorizon("30D", datetime(2026, 1, 2), datetime(2026, 1, 1))

    # Serialization
    d = h.to_dict()
    assert d["horizon_id"] == "90D"
    h2 = PortfolioHorizon.from_dict(d)
    assert h2.horizon_start == h.horizon_start

def test_allocation_score():
    score = make_score()
    assert score.raw_score == 0.85
    
    with pytest.raises(ValueError, match="raw_score must be a numeric value"):
        AllocationScore("invalid", 1.0, 1.0, 1.0)
        
    d = score.to_dict()
    assert d["raw_score"] == 0.85
    score2 = AllocationScore.from_dict(d)
    assert score2.performance_score == 0.9

def test_risk_budget_assignment():
    rb = RiskBudgetAssignment(0.05, 0.15)
    assert rb.tracking_error_pct == 0.05
    
    with pytest.raises(ValueError, match="tracking_error_pct must be a numeric value"):
        RiskBudgetAssignment("invalid", 0.15)
        
    d = rb.to_dict()
    rb2 = RiskBudgetAssignment.from_dict(d)
    assert rb2.max_drawdown_limit == 0.15

def test_allocation_recommendation():
    rec = make_recommendation()
    assert rec.recommended_weight == 0.25
    
    with pytest.raises(ValueError, match="recommended_weight must be a numeric value"):
        AllocationRecommendation("invalid", 0.20, RiskBudgetAssignment(0.05, 0.15))
    with pytest.raises(ValueError, match="risk_budget must be a RiskBudgetAssignment object"):
        AllocationRecommendation(0.25, 0.20, "invalid")
        
    d = rec.to_dict()
    rec2 = AllocationRecommendation.from_dict(d)
    assert rec2.recommended_capital_percentage == 0.20

def test_allocation_methodology_manifest():
    m = make_manifest()
    assert m.allocation_strategy_version == "v1.0"
    
    with pytest.raises(ValueError, match="allocation_methodology_urn must be a non-empty string"):
        AllocationMethodologyManifest("", "a" * 64, "v1.0")
        
    d = m.to_dict()
    m2 = AllocationMethodologyManifest.from_dict(d)
    assert m2.compute_hash() == m.compute_hash()


# 2. ALLOCATION SESSION AGGREGATE TESTS
def test_allocation_session_lifecycle():
    sess_id = str(uuid.uuid4())
    sess = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="WEIGHTED_FACTOR_V1"
    )
    assert sess.status == "INITIATED"
    
    # State transitions
    sess.start()
    assert sess.status == "CALCULATING"
    assert sess.aggregate_version == 2
    
    sess.complete()
    assert sess.status == "COMPLETED"
    assert sess.aggregate_version == 3
    
    sess.archive()
    assert sess.status == "ARCHIVED"
    assert sess.aggregate_version == 4
    
    # Invalid transition
    with pytest.raises(StateTransitionError, match="Cannot transition to CALCULATING"):
        sess.start()

def test_allocation_session_validation():
    sess_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Invalid session_urn format"):
        AllocationSession(sess_id, "invalid_urn", make_horizon(), "key")
    with pytest.raises(ValueError, match="horizon must be a PortfolioHorizon object"):
        AllocationSession(sess_id, f"urn:karsa:allocation:session:{sess_id}", "invalid", "key")
    with pytest.raises(ValueError, match="strategy_key must be a non-empty string"):
        AllocationSession(sess_id, f"urn:karsa:allocation:session:{sess_id}", make_horizon(), "")
    with pytest.raises(ValueError, match="Invalid session status"):
        AllocationSession(sess_id, f"urn:karsa:allocation:session:{sess_id}", make_horizon(), "key", status="invalid")

def test_allocation_session_immutability():
    sess_id = str(uuid.uuid4())
    sess = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="key"
    )
    # Allowed in INITIATED
    sess.strategy_key = "new_key"
    assert sess.strategy_key == "new_key"
    
    sess.start()
    sess.complete()
    
    # Mutating in COMPLETED must fail
    with pytest.raises(ImmutabilityViolationError):
        sess.strategy_key = "new_key2"
    with pytest.raises(ImmutabilityViolationError):
        del sess.strategy_key

def test_allocation_session_serialization():
    sess_id = str(uuid.uuid4())
    sess = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="key"
    )
    d = sess.to_dict()
    sess2 = AllocationSession.from_dict(d)
    assert sess2.session_id == sess.session_id


# 3. ALLOCATION DECISION RECORD AGGREGATE TESTS
def test_decision_record_lifecycle():
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
        allocation_manifest_hash=m.compute_hash(),
        allocation_version=1
    )
    assert record.is_active is True
    
    # Supersede
    record.supersede(next_version=2)
    assert record.is_active is False
    assert record.superseded_by_version == 2
    assert record.aggregate_version == 2
    
    # Cannot supersede/invalidate inactive record
    with pytest.raises(ImmutabilityViolationError):
        record.supersede(3)
    with pytest.raises(ImmutabilityViolationError):
        record.invalidate(3)

def test_decision_record_validation():
    rec_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())
    m = make_manifest()
    
    # URN and parameter validation
    with pytest.raises(ValueError, match="Invalid record_urn format"):
        AllocationDecisionRecord(rec_id, "invalid", f"urn:karsa:allocation:session:{sess_id}", "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())
    
    with pytest.raises(ValueError, match="Invalid session_urn format"):
        AllocationDecisionRecord(rec_id, f"urn:karsa:allocation:record:{rec_id}", "invalid", "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())

    with pytest.raises(ValueError, match="Invalid worker_urn format"):
        AllocationDecisionRecord(rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}", "invalid", "dec-1", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())

    with pytest.raises(ValueError, match="decision_id cannot be empty"):
        AllocationDecisionRecord(rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}", "urn:karsa:worker:w1", "", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash())

    with pytest.raises(ValueError, match="allocation_manifest_hash mismatch"):
        AllocationDecisionRecord(rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}", "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, "invalid_hash")

    # Predecessor URNs validation
    with pytest.raises(ValueError, match="Invalid supersedes_record_urn format"):
        AllocationDecisionRecord(rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}", "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash(), supersedes_record_urn="invalid")

    with pytest.raises(ValueError, match="Invalid invalidates_record_urn format"):
        AllocationDecisionRecord(rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}", "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(), m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash(), invalidates_record_urn="invalid")

def test_decision_record_immutability():
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
        allocation_manifest_hash=m.compute_hash(),
        allocation_version=1
    )
    # Mutate immutable attribute must fail
    with pytest.raises(ImmutabilityViolationError):
        record.worker_urn = "urn:karsa:worker:w2"
    with pytest.raises(ImmutabilityViolationError):
        del record.worker_urn

    # Mutate mutable attributes must succeed
    record.is_active = False
    assert record.is_active is False
    record.superseded_by_version = 2
    assert record.superseded_by_version == 2
    record.invalidated_by_version = 3
    assert record.invalidated_by_version == 3

    # Reactivating must fail
    with pytest.raises(ImmutabilityViolationError, match="Cannot reactivate"):
        record.is_active = True


# 4. DOMAIN EVENTS TESTS
def test_domain_events():
    evt_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Calculated
    evt_calc = AllocationCalculatedEvent(
        event_id=evt_id,
        correlation_id="urn:karsa:allocation:session:s1",
        causation_id="urn:karsa:allocation:record:r1",
        occurred_at=now,
        schema_version=1,
        record_urn="urn:karsa:allocation:record:r1",
        session_urn="urn:karsa:allocation:session:s1",
        worker_urn="urn:karsa:worker:w1",
        decision_id="dec-1",
        recommended_weight=0.25,
        allocation_version=1
    )
    assert evt_calc.recommended_weight == 0.25
    d = evt_calc.to_dict()
    evt_calc2 = AllocationCalculatedEvent.from_dict(d)
    assert evt_calc2.occurred_at == evt_calc.occurred_at

    # Superseded
    evt_super = AllocationSupersededEvent(
        event_id=evt_id,
        correlation_id="urn:karsa:allocation:session:s1",
        causation_id="urn:karsa:allocation:record:r2",
        occurred_at=now,
        schema_version=1,
        record_urn="urn:karsa:allocation:record:r1",
        superseded_by_record_urn="urn:karsa:allocation:record:r2",
        allocation_version=2
    )
    assert evt_super.allocation_version == 2
    d_super = evt_super.to_dict()
    evt_super2 = AllocationSupersededEvent.from_dict(d_super)
    assert evt_super2.superseded_by_record_urn == "urn:karsa:allocation:record:r2"

    # Invalidated
    evt_inv = AllocationInvalidatedEvent(
        event_id=evt_id,
        correlation_id="urn:karsa:allocation:session:s1",
        causation_id="urn:karsa:allocation:record:r1",
        occurred_at=now,
        schema_version=1,
        record_urn="urn:karsa:allocation:record:r1",
        invalidated_by_version=3
    )
    assert evt_inv.invalidated_by_version == 3
    d_inv = evt_inv.to_dict()
    evt_inv2 = AllocationInvalidatedEvent.from_dict(d_inv)
    assert evt_inv2.record_urn == "urn:karsa:allocation:record:r1"


# 5. LINEAGE UTILITIES TESTS
def test_reconstruct_allocation_lineage():
    sess_id = str(uuid.uuid4())
    m = make_manifest()
    
    r1_id = str(uuid.uuid4())
    r1 = AllocationDecisionRecord(
        record_id=r1_id,
        record_urn=f"urn:karsa:allocation:record:{r1_id}",
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
        is_active=False,
        superseded_by_version=2,
        allocation_version=1
    )
    
    r2_id = str(uuid.uuid4())
    r2 = AllocationDecisionRecord(
        record_id=r2_id,
        record_urn=f"urn:karsa:allocation:record:{r2_id}",
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
        supersedes_record_urn=r1.record_urn,
        is_active=False,
        superseded_by_version=3,
        allocation_version=2
    )

    r3_id = str(uuid.uuid4())
    r3 = AllocationDecisionRecord(
        record_id=r3_id,
        record_urn=f"urn:karsa:allocation:record:{r3_id}",
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
        supersedes_record_urn=r2.record_urn,
        is_active=True,
        allocation_version=3
    )

    records = [r1, r2, r3]
    
    # Normal lineage walk starting from any node
    lineage = reconstruct_allocation_lineage(records, r2.record_urn)
    assert len(lineage) == 3
    assert lineage[0].record_urn == r1.record_urn
    assert lineage[1].record_urn == r2.record_urn
    assert lineage[2].record_urn == r3.record_urn

    # Lineage walk starting from invalid URN
    assert reconstruct_allocation_lineage(records, "urn:karsa:allocation:record:nonexistent") == []

    # Invalidation walk
    r_inv_id = str(uuid.uuid4())
    r_inv = AllocationDecisionRecord(
        record_id=r_inv_id,
        record_urn=f"urn:karsa:allocation:record:{r_inv_id}",
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
        invalidates_record_urn=r3.record_urn,
        is_active=True,
        allocation_version=4
    )
    records.append(r_inv)
    r3.is_active = False
    r3.invalidated_by_version = 4
    
    lineage_inv = reconstruct_allocation_lineage(records, r_inv.record_urn)
    assert len(lineage_inv) == 4
    assert lineage_inv[3].record_urn == r_inv.record_urn

    # Loop protection test
    r_loop_id = str(uuid.uuid4())
    r_loop = AllocationDecisionRecord(
        record_id=r_loop_id,
        record_urn=f"urn:karsa:allocation:record:{r_loop_id}",
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
        supersedes_record_urn=f"urn:karsa:allocation:record:{r_loop_id}",  # Point to self to create cycle
        is_active=True,
        allocation_version=1
    )
    loop_lineage = reconstruct_allocation_lineage([r_loop], r_loop.record_urn)
    assert len(loop_lineage) == 1


def test_value_object_edge_cases():
    # PortfolioHorizon invalid checks
    with pytest.raises(ValueError, match="horizon_id must be a non-empty string"):
        PortfolioHorizon(123, datetime.now(timezone.utc), datetime.now(timezone.utc))

    # AllocationScore non-numeric validation
    with pytest.raises(ValueError, match="raw_score must be a numeric value"):
        AllocationScore("invalid", 1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="performance_score must be a numeric value"):
        AllocationScore(1.0, "invalid", 1.0, 1.0)
    with pytest.raises(ValueError, match="attribution_score must be a numeric value"):
        AllocationScore(1.0, 1.0, "invalid", 1.0)
    with pytest.raises(ValueError, match="review_penalty_multiplier must be a numeric value"):
        AllocationScore(1.0, 1.0, 1.0, "invalid")

    # RiskBudgetAssignment non-numeric validation
    with pytest.raises(ValueError, match="tracking_error_pct must be a numeric value"):
        RiskBudgetAssignment("invalid", 0.1)
    with pytest.raises(ValueError, match="max_drawdown_limit must be a numeric value"):
        RiskBudgetAssignment(0.1, "invalid")

    # AllocationRecommendation validations
    with pytest.raises(ValueError, match="recommended_capital_percentage must be a numeric value"):
        AllocationRecommendation(0.2, "invalid", RiskBudgetAssignment(0.05, 0.15))

    # AllocationMethodologyManifest validations
    with pytest.raises(ValueError, match="allocation_policy_hash must be a non-empty string"):
        AllocationMethodologyManifest("urn:karsa:methodology:1", "", "v1")
    with pytest.raises(ValueError, match="allocation_strategy_version must be a non-empty string"):
        AllocationMethodologyManifest("urn:karsa:methodology:1", "hash", None)


def test_allocation_session_edge_cases():
    sess_id = str(uuid.uuid4())
    sess = AllocationSession(
        session_id=sess_id,
        session_urn=f"urn:karsa:allocation:session:{sess_id}",
        horizon=make_horizon(),
        strategy_key="WEIGHTED_FACTOR_V1"
    )
    # Test __delattr__ during active states
    sess.temp_attr = "temp"
    assert sess.temp_attr == "temp"
    del sess.temp_attr
    assert not hasattr(sess, "temp_attr")

    # Test __delattr__ when _initialized is False
    sess._initialized = False
    sess.temp_attr2 = "temp2"
    del sess.temp_attr2
    assert not hasattr(sess, "temp_attr2")
    sess._initialized = True

    # Test complete() from INITIATED
    with pytest.raises(StateTransitionError, match="Cannot transition to COMPLETED from INITIATED"):
        sess.complete()

    # Test archive() from CALCULATING
    sess.start()
    with pytest.raises(StateTransitionError, match="Cannot transition to ARCHIVED from CALCULATING"):
        sess.archive()


def test_decision_record_edge_cases():
    rec_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())
    m = make_manifest()

    # Invalid objects
    with pytest.raises(ValueError, match="horizon must be a PortfolioHorizon object"):
        AllocationDecisionRecord(
            rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
            "urn:karsa:worker:w1", "dec-1", "not-a-horizon", make_score(), make_recommendation(),
            m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash()
        )

    with pytest.raises(ValueError, match="allocation_score must be an AllocationScore object"):
        AllocationDecisionRecord(
            rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
            "urn:karsa:worker:w1", "dec-1", make_horizon(), "not-a-score", make_recommendation(),
            m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash()
        )

    with pytest.raises(ValueError, match="recommendation must be an AllocationRecommendation object"):
        AllocationDecisionRecord(
            rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
            "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), "not-a-recommendation",
            m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash()
        )

    # Version validations < 1
    with pytest.raises(ValueError, match="superseded_by_version must be positive integer >= 1"):
        AllocationDecisionRecord(
            rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
            "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(),
            m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash(),
            superseded_by_version=0
        )

    with pytest.raises(ValueError, match="invalidated_by_version must be positive integer >= 1"):
        AllocationDecisionRecord(
            rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
            "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(),
            m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash(),
            invalidated_by_version=0
        )

    with pytest.raises(ValueError, match="allocation_version must be positive integer >= 1"):
        AllocationDecisionRecord(
            rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
            "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(),
            m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash(),
            allocation_version=0
        )

    # Test deleting an attribute when _initialized = False
    record = AllocationDecisionRecord(
        rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
        "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(),
        m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash()
    )
    object.__setattr__(record, "_initialized", False)
    record.temp_attr = "val"
    del record.temp_attr
    assert not hasattr(record, "temp_attr")

    # Invalidate active record
    record = AllocationDecisionRecord(
        rec_id, f"urn:karsa:allocation:record:{rec_id}", f"urn:karsa:allocation:session:{sess_id}",
        "urn:karsa:worker:w1", "dec-1", make_horizon(), make_score(), make_recommendation(),
        m.allocation_methodology_urn, m.allocation_policy_hash, m.allocation_strategy_version, m.compute_hash()
    )
    assert record.is_active is True
    record.invalidate(invalidating_version=5)
    assert record.is_active is False
    assert record.invalidated_by_version == 5
    assert record.aggregate_version == 2


def test_domain_events_edge_cases():
    evt_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # DomainEvent base validations
    with pytest.raises(ValueError, match="correlation_id cannot be empty"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="causation_id cannot be empty"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="occurred_at must be a datetime object"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at="invalid", schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="schema_version must be positive integer >= 1"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=0, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    # AllocationCalculatedEvent validations
    with pytest.raises(ValueError, match="Invalid record_urn"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="invalid_record",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="Invalid session_urn"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="invalid_session", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="Invalid worker_urn"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="invalid_worker",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="decision_id cannot be empty"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="", recommended_weight=0.25, allocation_version=1
        )

    with pytest.raises(ValueError, match="recommended_weight must be a numeric value"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight="invalid", allocation_version=1
        )

    with pytest.raises(ValueError, match="allocation_version must be positive integer >= 1"):
        AllocationCalculatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            session_urn="urn:karsa:allocation:session:s1", worker_urn="urn:karsa:worker:w1",
            decision_id="dec-1", recommended_weight=0.25, allocation_version=0
        )

    # AllocationSupersededEvent validations
    with pytest.raises(ValueError, match="Invalid record_urn"):
        AllocationSupersededEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r2",
            occurred_at=now, schema_version=1, record_urn="invalid_record",
            superseded_by_record_urn="urn:karsa:allocation:record:r2", allocation_version=2
        )

    with pytest.raises(ValueError, match="Invalid superseded_by_record_urn"):
        AllocationSupersededEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r2",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            superseded_by_record_urn="invalid_record", allocation_version=2
        )

    with pytest.raises(ValueError, match="allocation_version must be positive integer >= 1"):
        AllocationSupersededEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r2",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1",
            superseded_by_record_urn="urn:karsa:allocation:record:r2", allocation_version=0
        )

    # AllocationInvalidatedEvent validations
    with pytest.raises(ValueError, match="Invalid record_urn"):
        AllocationInvalidatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="invalid_record", invalidated_by_version=3
        )

    with pytest.raises(ValueError, match="invalidated_by_version must be positive integer >= 1"):
        AllocationInvalidatedEvent(
            event_id=evt_id, correlation_id="urn:karsa:allocation:session:s1", causation_id="urn:karsa:allocation:record:r1",
            occurred_at=now, schema_version=1, record_urn="urn:karsa:allocation:record:r1", invalidated_by_version=0
        )
