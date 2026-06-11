import pytest
from pathlib import Path
from karsa.review.registry import IssueRegistry
from karsa.review.convergence import ReviewConvergenceEngine
from karsa.review.models import IssueStatus
import textwrap

def test_scenario_a_convergence(tmp_path: Path):
    registry = IssueRegistry(tmp_path)
    engine = ReviewConvergenceEngine(registry)
    
    review_1 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # New Issues
    Issue: A001
    Severity: BLOCKING
    
    Description:
    1
    
    Evidence:
    1
    
    Issue: A002
    Severity: BLOCKING
    
    Description:
    2
    
    Evidence:
    2
    
    Issue: A003
    Severity: BLOCKING
    
    Description:
    3
    
    Evidence:
    3
    
    Issue: A004
    Severity: BLOCKING
    
    Description:
    4
    
    Evidence:
    4
    
    Issue: A005
    Severity: BLOCKING
    
    Description:
    5
    
    Evidence:
    5
    
    # Summary
    """)
    engine.process_review(review_1, 1)
    metrics = engine.get_metrics()
    assert metrics["blocking_issue_count"] == 5
    assert not engine.should_approve()

    review_2 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # Existing Issues
    Issue: P001
    Status: RESOLVED
    
    Issue: P002
    Status: RESOLVED
    
    Issue: P003
    Status: OPEN
    
    Issue: P004
    Status: OPEN
    
    Issue: P005
    Status: OPEN
    
    # New Issues
    # Summary
    """)
    engine.process_review(review_2, 2)
    metrics = engine.get_metrics()
    assert metrics["blocking_issue_count"] == 3
    assert not engine.should_approve()

    review_3 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # Existing Issues
    Issue: P003
    Status: RESOLVED
    
    Issue: P004
    Status: RESOLVED
    
    Issue: P005
    Status: OPEN
    
    # New Issues
    # Summary
    """)
    engine.process_review(review_3, 3)
    metrics = engine.get_metrics()
    assert metrics["blocking_issue_count"] == 1
    assert not engine.should_approve()

    review_4 = textwrap.dedent("""\
    # Review Result
    Outcome: APPROVE
    
    # Existing Issues
    Issue: P005
    Status: RESOLVED
    
    # New Issues
    # Summary
    """)
    engine.process_review(review_4, 4)
    metrics = engine.get_metrics()
    assert metrics["blocking_issue_count"] == 0
    assert engine.should_approve()

def test_scenario_c_reopen(tmp_path: Path):
    registry = IssueRegistry(tmp_path)
    engine = ReviewConvergenceEngine(registry)
    
    review_1 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # New Issues
    Issue: A001
    Severity: BLOCKING
    
    Description:
    1
    
    Evidence:
    1
    
    # Summary
    
    # Confidence
    0.90
    """)
    engine.process_review(review_1, 1)
    assert registry.issues["P001"].status == IssueStatus.OPEN
    
    review_2 = textwrap.dedent("""\
    # Review Result
    Outcome: APPROVE
    
    # Existing Issues
    Issue: P001
    Status: RESOLVED
    
    # New Issues
    # Summary
    
    # Confidence
    0.90
    """)
    engine.process_review(review_2, 2)
    assert registry.issues["P001"].status == IssueStatus.RESOLVED

    review_3 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # Existing Issues
    Issue: P001
    Status: REOPENED
    
    # New Issues
    # Summary
    
    # Confidence
    0.90
    """)
    engine.process_review(review_3, 3)
    assert registry.issues["P001"].status == IssueStatus.REOPENED

def test_scenario_issue_freeze(tmp_path: Path):
    registry = IssueRegistry(tmp_path)
    engine = ReviewConvergenceEngine(registry)
    
    review_1 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # New Issues
    Issue: A001
    Severity: BLOCKING
    
    Description:
    1
    
    Evidence:
    1
    
    # Summary
    
    # Confidence
    0.90
    """)
    engine.process_review(review_1, 1)
    assert len(registry.issues) == 1
    
    review_2 = textwrap.dedent("""\
    # Review Result
    Outcome: REJECT
    
    # New Issues
    Issue: A002
    Severity: BLOCKING
    
    Description:
    This is a normal issue, a completely new bug
    
    Evidence:
    2
    
    Issue: A003
    Severity: BLOCKING
    
    Description:
    This is a regression caused by the latest changes
    
    Evidence:
    3
    
    # Summary
    
    # Confidence
    0.90
    """)
    engine.process_review(review_2, 2)
    # A002 should be dropped, A003 should be kept because it has "regression" in description
    assert len(registry.issues) == 2
    assert "P001" in registry.issues
    assert "P002" in registry.issues
    assert "regression" in registry.issues["P002"].description.lower()
