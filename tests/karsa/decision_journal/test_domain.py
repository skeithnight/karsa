import pytest
from decimal import Decimal
from datetime import datetime
from karsa.decision_journal.domain.value_objects import (
    ConfidenceLevel, InvalidationCriteria, ExpectedOutcome, ExpectedHorizon, JournalHash
)
from karsa.decision_journal.domain.exceptions import (
    InvalidConfidenceError, TemporalLineageError, CryptographicIntegrityError
)
from karsa.decision_journal.domain.events import DecisionJournalAppended
from karsa.decision_journal.domain.models import DecisionJournalEntry
from karsa.decision_journal.domain.lineage import validate_journal_lineage

def test_confidence_level():
    ConfidenceLevel(Decimal("0.5"))
    with pytest.raises(InvalidConfidenceError):
        ConfidenceLevel(Decimal("1.1"))
    with pytest.raises(InvalidConfidenceError):
        ConfidenceLevel(Decimal("-0.1"))

def test_invalidation_criteria():
    InvalidationCriteria("Valid criteria")
    with pytest.raises(ValueError):
        InvalidationCriteria("   ")

def test_expected_horizon():
    ExpectedHorizon(30)
    with pytest.raises(ValueError):
        ExpectedHorizon(0)

def test_decision_journal_appended():
    dt = datetime.utcnow()
    e = DecisionJournalAppended("j_urn", "t_urn", "w_urn", "s_urn", "c_urn", None, "hash", dt)
    assert e.journal_urn == "j_urn"

def test_decision_journal_entry():
    dt = datetime.utcnow()
    c = ConfidenceLevel(Decimal("0.8"))
    i = InvalidationCriteria("price drops 10%")
    o = ExpectedOutcome(Decimal("150"), "price")
    h = ExpectedHorizon(30)
    jh = JournalHash("hash123")
    entry = DecisionJournalEntry("j1", "t1", "w1", "s1", "c1", None, jh, c, "rationale", ["ev1"], ["risk1"], i, o, h, dt)
    assert entry.journal_urn == "j1"

def test_lineage():
    dt1 = datetime(2026, 1, 1)
    dt2 = datetime(2026, 1, 2)
    dt3 = datetime(2026, 1, 3)
    
    c = ConfidenceLevel(Decimal("0.8"))
    i = InvalidationCriteria("test")
    o = ExpectedOutcome(Decimal("150"), "price")
    h = ExpectedHorizon(30)
    
    # Valid lineage
    jh1 = JournalHash.generate("j1", "t1", None)
    e1 = DecisionJournalEntry("j1", "t1", "w1", None, None, None, jh1, c, "r", [], [], i, o, h, dt1)
    
    jh2 = JournalHash.generate("j2", "t1", jh1.hash_value)
    e2 = DecisionJournalEntry("j2", "t1", "w1", None, None, "j1", jh2, c, "r", [], [], i, o, h, dt2)
    
    validate_journal_lineage([e1, e2])
    
    # Cycle detection
    e_cycle = DecisionJournalEntry("j1", "t1", "w1", None, None, "j2", jh1, c, "r", [], [], i, o, h, dt3)
    with pytest.raises(TemporalLineageError):
        validate_journal_lineage([e1, e2, e_cycle])
        
    # Hash corruption
    jh_bad = JournalHash("bad_hash")
    e_corrupt = DecisionJournalEntry("j3", "t1", "w1", None, None, "j2", jh_bad, c, "r", [], [], i, o, h, dt3)
    with pytest.raises(CryptographicIntegrityError):
        validate_journal_lineage([e1, e2, e_corrupt])
        
    # Missing parent
    e_missing_parent = DecisionJournalEntry("j4", "t1", "w1", None, None, "missing_parent", jh_bad, c, "r", [], [], i, o, h, dt3)
    with pytest.raises(TemporalLineageError):
        validate_journal_lineage([e1, e2, e_missing_parent])
