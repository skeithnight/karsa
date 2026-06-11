"""Golden tests for the review parsing pipeline.

These tests use real Gemini-style review outputs as fixtures to validate
the entire parsing pipeline: outcome extraction, issue extraction, 
blocking counts, and fail-closed safety mechanisms.
"""
import pytest
from pathlib import Path
from karsa.review.registry import IssueRegistry
from karsa.review.convergence import ReviewConvergenceEngine, ReviewParsingException
from karsa.review.models import IssueStatus
import textwrap
import json


# ============================================================================
# GOLDEN FIXTURES - Real Gemini-style review outputs
# ============================================================================

GOLDEN_REJECT_WITH_BLOCKING = textwrap.dedent("""\
# Review Result

Outcome: REJECT

# Existing Issues

# New Issues

Issue: ARCH-001
Severity: BLOCKING

Description:
The architecture uses a monolithic design pattern that will not scale beyond 1000 concurrent users. The single-process model described in ARCHITECTURE.md section 3.2 creates a bottleneck at the request handling layer.

Evidence:
> "All requests are processed sequentially through a single event loop" - ARCHITECTURE.md, Section 3.2

Issue: ARCH-002
Severity: BLOCKING

Description:
No database migration strategy defined. The implementation plan references PostgreSQL schema changes but provides no rollback mechanism or version control for migrations.

Evidence:
> "Database schema will be updated directly" - IMPLEMENTATION_PLAN.md, Section 5.1

Issue: IMPL-001
Severity: BLOCKING

Description:
The authentication module uses a hardcoded JWT secret key. This is a critical security vulnerability that would expose all user sessions if the source code is compromised.

Evidence:
> "const JWT_SECRET = 'karsa-default-secret'" - IMPLEMENTATION_PLAN.md, Section 4.3

Issue: OPS-001
Severity: BLOCKING

Description:
No monitoring or alerting strategy defined. The system has no health check endpoints, no metrics collection, and no error reporting mechanism.

Evidence:
> The ARCHITECTURE.md document contains no mention of monitoring, observability, or alerting infrastructure.

Issue: PROD-001
Severity: NON_BLOCKING

Description:
The product vision mentions "AI-powered recommendations" but the implementation plan contains no ML pipeline or model serving infrastructure.

Evidence:
> "Leverage AI to provide personalized recommendations" - VISION.md, Section 2.1
> No corresponding implementation section found.

Issue: COST-001
Severity: NON_BLOCKING

Description:
No cost estimation for cloud infrastructure. The architecture assumes auto-scaling but provides no budget constraints or cost monitoring.

Evidence:
> "Deploy on auto-scaling cloud infrastructure" - ARCHITECTURE.md, Section 6.1

# Summary

Open Blocking Issues: 4
Open Non Blocking Issues: 2

# Confidence
0.92
""")


GOLDEN_APPROVE_CLEAN = textwrap.dedent("""\
# Review Result

Outcome: APPROVE

# Existing Issues

Issue: P001
Status: RESOLVED

Issue: P002
Status: RESOLVED

# New Issues

# Summary

Open Blocking Issues: 0
Open Non Blocking Issues: 0

# Confidence
0.95
""")


GOLDEN_REJECT_VARIANT_FORMAT = textwrap.dedent("""\
# Review Result

Outcome:  REJECT

## Existing Issues

## New Issues

Issue:  SEC-001
Severity:  BLOCKING

Description:
SQL injection vulnerability in user search endpoint.

Evidence:
Raw string concatenation used in query builder.

Issue:  SEC-002
Severity:  NON_BLOCKING

Description:
CSRF tokens not validated on form submissions.

Evidence:
No CSRF middleware configured.

## Summary

Open Blocking Issues: 1
Open Non Blocking Issues: 1

## Confidence
0.88
""")


GOLDEN_REJECT_NO_SUMMARY_HEADER = textwrap.dedent("""\
# Review Result

Outcome: REJECT

# New Issues

Issue: ARCH-001
Severity: BLOCKING

Description:
Missing load balancer configuration.

Evidence:
No load balancing mentioned in architecture.

Issue: ARCH-002
Severity: BLOCKING

Description:
No caching strategy defined.

Evidence:
No Redis or memcached in dependencies.

# Confidence
0.85
""")


# ============================================================================
# GOLDEN TESTS - Outcome extraction
# ============================================================================

class TestGoldenRejectWithBlocking:
    """Tests for a standard REJECT review with 4 blocking + 2 non-blocking issues."""

    def test_extracts_all_blocking_issues(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        engine.process_review(GOLDEN_REJECT_WITH_BLOCKING, 1)
        
        metrics = engine.get_metrics()
        assert metrics["blocking_issue_count"] == 4
        assert metrics["non_blocking_issue_count"] == 2
        assert not engine.should_approve()

    def test_diagnostics_match(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        diagnostics = engine.process_review(GOLDEN_REJECT_WITH_BLOCKING, 1)
        
        assert diagnostics["detected_outcome"] == "REJECT"
        assert diagnostics["extracted_new_blocking"] == 4
        assert diagnostics["extracted_new_non_blocking"] == 2
        assert diagnostics["confidence"] == 0.92
        assert diagnostics["issue_extraction_failed"] is False
        assert len(diagnostics["parse_warnings"]) == 0

    def test_should_approve_safe_returns_false(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        diagnostics = engine.process_review(GOLDEN_REJECT_WITH_BLOCKING, 1)
        
        assert not engine.should_approve_safe(diagnostics)


class TestGoldenApproveClean:
    """Tests for a clean APPROVE review that resolves all existing issues."""

    def test_approve_with_resolved_issues(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        # Pre-populate with 2 blocking issues that will be resolved
        registry.add_issue("BLOCKING", "Issue 1", "Evidence 1", 1)
        registry.add_issue("BLOCKING", "Issue 2", "Evidence 2", 1)
        assert len(registry.get_blocking_issues()) == 2
        
        diagnostics = engine.process_review(GOLDEN_APPROVE_CLEAN, 2)
        
        assert diagnostics["detected_outcome"] == "APPROVE"
        assert diagnostics["confidence"] == 0.95
        assert engine.should_approve()
        assert engine.should_approve_safe(diagnostics)


class TestGoldenRejectVariantFormat:
    """Tests for REJECT review with ## headings and extra whitespace."""

    def test_extracts_issues_with_variant_format(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        diagnostics = engine.process_review(GOLDEN_REJECT_VARIANT_FORMAT, 1)
        
        metrics = engine.get_metrics()
        assert metrics["blocking_issue_count"] == 1
        assert metrics["non_blocking_issue_count"] == 1
        assert diagnostics["detected_outcome"] == "REJECT"
        assert diagnostics["extracted_new_blocking"] == 1
        assert diagnostics["extracted_new_non_blocking"] == 1
        assert not engine.should_approve()


class TestGoldenRejectNoSummaryHeader:
    """Tests for REJECT review missing # Summary header - THE EXACT BUG SCENARIO."""

    def test_extracts_issues_without_summary(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        diagnostics = engine.process_review(GOLDEN_REJECT_NO_SUMMARY_HEADER, 1)
        
        metrics = engine.get_metrics()
        assert metrics["blocking_issue_count"] == 2
        assert diagnostics["detected_outcome"] == "REJECT"
        assert diagnostics["extracted_new_blocking"] == 2
        assert not engine.should_approve()


# ============================================================================
# PARSER VALIDATION TESTS - Fail-closed behavior
# ============================================================================

class TestParserValidation:
    """Tests that parser validation catches extraction failures."""

    def test_blocking_mismatch_raises_exception(self, tmp_path: Path):
        """If review contains 'Severity: BLOCKING' but parser extracts 0 blocking issues,
        ReviewParsingException must be raised."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        # Review with BLOCKING text outside the # New Issues section
        # (malformed issue block that regex can't parse)
        review = textwrap.dedent("""\
        # Review Result
        
        Outcome: REJECT
        
        This review contains Severity: BLOCKING issues that are not properly formatted.
        
        # New Issues
        
        The issues are malformed and cannot be parsed:
        ARCH-001 is BLOCKING
        ARCH-002 is BLOCKING
        
        # Summary
        
        # Confidence
        0.90
        """)
        
        with pytest.raises(ReviewParsingException):
            engine.process_review(review, 1)

    def test_reject_with_zero_registry_raises_exception(self, tmp_path: Path):
        """If outcome is REJECT but registry has 0 active issues, raise exception."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        review = textwrap.dedent("""\
        # Review Result
        
        Outcome: REJECT
        
        # New Issues
        
        No properly formatted issues here.
        
        # Summary
        
        # Confidence
        0.90
        """)
        
        with pytest.raises(ReviewParsingException):
            engine.process_review(review, 1)

    def test_unknown_outcome_raises_exception(self, tmp_path: Path):
        """If outcome cannot be parsed, raise exception."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        review = textwrap.dedent("""\
        # Review Result
        
        This review has no outcome line at all.
        
        # New Issues
        
        # Summary
        
        # Confidence
        0.90
        """)
        
        with pytest.raises(ReviewParsingException):
            engine.process_review(review, 1)

    def test_low_confidence_with_extraction_failure_raises(self, tmp_path: Path):
        """Low confidence + extraction failure = exception."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        # No # New Issues section AND low confidence
        review = textwrap.dedent("""\
        # Review Result
        
        Outcome: APPROVE
        
        Some unstructured review text without proper sections.
        
        # Confidence
        0.30
        """)
        
        with pytest.raises(ReviewParsingException):
            engine.process_review(review, 1)


# ============================================================================
# FAIL-CLOSED TESTS - The exact bug reproduction
# ============================================================================

class TestFailClosed:
    """Tests that the system never silently converts REJECT to APPROVE."""

    def test_never_approves_empty_reject(self, tmp_path: Path):
        """THE EXACT BUG REPRODUCTION:
        
        Review says REJECT with BLOCKING issues, but section headers are
        malformed so regex fails to extract them. The old code would:
        1. Fail to extract issues (registry stays empty)
        2. should_approve() returns True (0 blocking issues)
        3. Overwrite outcome to APPROVE
        
        The fix must raise ReviewParsingException instead.
        """
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        # This review uses a completely non-standard format that the regex
        # cannot parse - simulating a real LLM format deviation
        review = textwrap.dedent("""\
        # Review Result
        
        Outcome: REJECT
        
        ## Review Findings
        
        The following critical issues were found:
        
        ### ARCH-001 (Severity: BLOCKING)
        Missing database migration strategy.
        Evidence: No migration tooling referenced.
        
        ### ARCH-002 (Severity: BLOCKING)
        No caching layer defined.
        Evidence: No Redis/memcached in deps.
        
        # Confidence
        0.88
        """)
        
        with pytest.raises(ReviewParsingException):
            engine.process_review(review, 1)

    def test_should_approve_safe_rejects_when_outcome_is_reject(self, tmp_path: Path):
        """should_approve_safe must return False when detected_outcome is REJECT,
        even if registry has 0 blocking issues."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        diagnostics = {
            "detected_outcome": "REJECT",
            "extracted_new_blocking": 0,
            "extracted_new_non_blocking": 2,
            "parse_warnings": [],
            "confidence": 0.9,
            "issue_extraction_failed": False
        }
        
        assert not engine.should_approve_safe(diagnostics)

    def test_should_approve_safe_rejects_on_extraction_failure(self, tmp_path: Path):
        """should_approve_safe must return False when issue extraction failed."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        diagnostics = {
            "detected_outcome": "APPROVE",
            "extracted_new_blocking": 0,
            "extracted_new_non_blocking": 0,
            "parse_warnings": ["Could not find '# New Issues' section."],
            "confidence": 0.9,
            "issue_extraction_failed": True
        }
        
        assert not engine.should_approve_safe(diagnostics)

    def test_should_approve_safe_approves_clean_review(self, tmp_path: Path):
        """should_approve_safe returns True for a genuinely clean APPROVE."""
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        
        diagnostics = {
            "detected_outcome": "APPROVE",
            "extracted_new_blocking": 0,
            "extracted_new_non_blocking": 0,
            "parse_warnings": [],
            "confidence": 0.95,
            "issue_extraction_failed": False
        }
        
        assert engine.should_approve_safe(diagnostics)


# ============================================================================
# DIAGNOSTICS PERSISTENCE TESTS
# ============================================================================

class TestDiagnosticsPersistence:
    """Tests for parser_debug.json persistence."""

    def test_parser_debug_json_persisted(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        engine.process_review(GOLDEN_REJECT_WITH_BLOCKING, 1)
        
        debug_file = tmp_path / ".karsa" / "parser_debug.json"
        assert debug_file.exists()
        
        with open(debug_file) as f:
            debug_data = json.load(f)
        
        assert "detected_outcome" in debug_data
        assert "extracted_new_blocking" in debug_data
        assert "extracted_new_non_blocking" in debug_data
        assert "parse_warnings" in debug_data
        assert "raw_review_hash" in debug_data
        assert "confidence" in debug_data
        assert "issue_extraction_failed" in debug_data
        
        assert debug_data["detected_outcome"] == "REJECT"
        assert debug_data["extracted_new_blocking"] == 4
        assert debug_data["extracted_new_non_blocking"] == 2
        assert debug_data["confidence"] == 0.92
        assert debug_data["issue_extraction_failed"] is False
        assert len(debug_data["raw_review_hash"]) == 64  # SHA-256 hex digest

    def test_diagnostics_stored_on_engine(self, tmp_path: Path):
        registry = IssueRegistry(tmp_path)
        engine = ReviewConvergenceEngine(registry)
        diagnostics = engine.process_review(GOLDEN_REJECT_WITH_BLOCKING, 1)
        
        assert engine._last_diagnostics is not None
        assert engine._last_diagnostics == diagnostics
