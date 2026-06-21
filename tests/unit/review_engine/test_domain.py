"""Review Engine domain tests — Sprint-10 Wave-1."""
import pytest
from datetime import datetime

from karsa.review_engine.domain.aggregates.review_assessment import (
    ReviewAssessment, ImmutableLedgerEntry, MAX_FINDINGS, MAX_RECOMMENDATIONS,
)
from karsa.review_engine.domain.entities.review_finding import ReviewFinding
from karsa.review_engine.domain.entities.review_recommendation import ReviewRecommendation
from karsa.review_engine.domain.value_objects.enums import (
    ReviewType, FindingType, FindingSeverity,
    RecommendationType, RecommendationPriority,
    ReviewStatus, QualitySource,
)
from karsa.review_engine.domain.value_objects.review_evidence import ReviewEvidence
from karsa.review_engine.domain.value_objects.review_summary import ReviewSummary
from karsa.review_engine.domain.value_objects.review_quality import ReviewQuality
from karsa.review_engine.domain.value_objects.review_context_snapshot import ReviewContextSnapshot
from karsa.review_engine.domain.value_objects.recommendation_impact import RecommendationImpact
from karsa.review_engine.domain.exceptions import (
    ReviewDomainError, InvalidReviewError, SizeGuardrailExceededError,
    InvalidFindingError, InvalidRecommendationError,
)


# --- Factories ---

def _make_evidence():
    return ReviewEvidence(
        source_type="PERFORMANCE",
        source_id="eval-1",
        data_points={"score": 0.8},
        explanation="test evidence",
    )


def _make_finding(**overrides):
    defaults = dict(
        finding_id="f1",
        dimension="THESIS",
        finding_type=FindingType.OBSERVATION,
        severity=FindingSeverity.MEDIUM,
        description="Test finding",
        evidence=_make_evidence(),
        confidence=0.7,
        created_at=datetime.utcnow().isoformat(),
    )
    defaults.update(overrides)
    return ReviewFinding(**defaults)


def _make_recommendation(**overrides):
    defaults = dict(
        recommendation_id="r1",
        finding_id="f1",
        recommendation_type=RecommendationType.ADJUST_ALLOCATION,
        priority=RecommendationPriority.MEDIUM,
        description="Test recommendation",
        expected_impact="Improved returns",
        implementation_risk="Low",
        created_at=datetime.utcnow().isoformat(),
    )
    defaults.update(overrides)
    return ReviewRecommendation(**defaults)


def _make_summary():
    return ReviewSummary(
        total_findings=1,
        findings_by_severity={"MEDIUM": 1},
        total_recommendations=1,
        recommendations_by_priority={"MEDIUM": 1},
        overall_assessment="NEUTRAL",
        confidence=0.7,
        explanation="Test summary",
    )


def _make_quality():
    return ReviewQuality(
        quality_score=0.7,
        data_completeness=1.0,
        analysis_depth=0.8,
    )


def _make_snapshot():
    return ReviewContextSnapshot(
        evaluation_snapshot={"id": "eval-1"},
        decision_snapshot={"id": "dec-1"},
        snapshot_hash="abc123",
    )


def _make_assessment(**overrides):
    defaults = dict(
        review_id="rev-1",
        evaluation_id="eval-1",
        review_type=ReviewType.WORKER,
        review_version="v1.0",
        target_urn="worker-1",
        target_type="WORKER",
        decision_id="dec-1",
        attribution_id="attr-1",
        findings=[_make_finding()],
        recommendations=[_make_recommendation()],
        review_summary=_make_summary(),
        review_quality=_make_quality(),
        context_snapshot=_make_snapshot(),
        reviewed_at=datetime.utcnow(),
        reviewed_by="test",
    )
    defaults.update(overrides)
    return ReviewAssessment(**defaults)


# --- Enum Tests ---

class TestEnums:
    def test_review_type_values(self):
        assert ReviewType.WORKER == "WORKER"
        assert ReviewType.THESIS == "THESIS"
        assert ReviewType.ALLOCATION == "ALLOCATION"
        assert ReviewType.REGIME == "REGIME"
        assert ReviewType.PORTFOLIO == "PORTFOLIO"

    def test_finding_type_values(self):
        assert FindingType.OBSERVATION == "OBSERVATION"
        assert FindingType.CONCERN == "CONCERN"
        assert FindingType.RISK == "RISK"
        assert FindingType.OPPORTUNITY == "OPPORTUNITY"

    def test_finding_severity_values(self):
        assert FindingSeverity.LOW == "LOW"
        assert FindingSeverity.MEDIUM == "MEDIUM"
        assert FindingSeverity.HIGH == "HIGH"
        assert FindingSeverity.CRITICAL == "CRITICAL"

    def test_recommendation_type_values(self):
        assert RecommendationType.ADJUST_ALLOCATION == "ADJUST_ALLOCATION"
        assert RecommendationType.PAUSE_WORKER == "PAUSE_WORKER"
        assert RecommendationType.ESCALATE == "ESCALATE"
        assert RecommendationType.NO_ACTION == "NO_ACTION"

    def test_recommendation_priority_values(self):
        assert RecommendationPriority.LOW == "LOW"
        assert RecommendationPriority.MEDIUM == "MEDIUM"
        assert RecommendationPriority.HIGH == "HIGH"
        assert RecommendationPriority.URGENT == "URGENT"

    def test_review_status_values(self):
        assert ReviewStatus.CANONICAL == "CANONICAL"
        assert ReviewStatus.SUPERSEDED == "SUPERSEDED"
        assert ReviewStatus.EXPERIMENTAL == "EXPERIMENTAL"

    def test_quality_source_values(self):
        assert QualitySource.SYSTEM_DEFAULT == "SYSTEM_DEFAULT"
        assert QualitySource.MANUAL_REVIEW == "MANUAL_REVIEW"
        assert QualitySource.PERFORMANCE_ENGINE == "PERFORMANCE_ENGINE"
        assert QualitySource.ATTRIBUTION_ENGINE == "ATTRIBUTION_ENGINE"


# --- ReviewEvidence Tests ---

class TestReviewEvidence:
    def test_valid_evidence(self):
        e = _make_evidence()
        assert e.source_type == "PERFORMANCE"

    def test_empty_source_type_raises(self):
        with pytest.raises(ValueError, match="source_type"):
            ReviewEvidence(source_type="", source_id="e1", data_points={}, explanation="test")

    def test_frozen(self):
        e = _make_evidence()
        with pytest.raises(AttributeError):
            e.source_type = "changed"


# --- ReviewSummary Tests ---

class TestReviewSummary:
    def test_valid_summary(self):
        s = _make_summary()
        assert s.overall_assessment == "NEUTRAL"

    def test_invalid_assessment_raises(self):
        with pytest.raises(ValueError, match="overall_assessment"):
            ReviewSummary(
                total_findings=1, findings_by_severity={},
                total_recommendations=1, recommendations_by_priority={},
                overall_assessment="INVALID", confidence=0.5, explanation="test",
            )

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            ReviewSummary(
                total_findings=1, findings_by_severity={},
                total_recommendations=1, recommendations_by_priority={},
                overall_assessment="NEUTRAL", confidence=1.5, explanation="test",
            )


# --- ReviewQuality Tests ---

class TestReviewQuality:
    def test_valid_quality(self):
        q = _make_quality()
        assert q.is_sufficient is True

    def test_insufficient_quality(self):
        q = ReviewQuality(quality_score=0.2, data_completeness=0.5, analysis_depth=0.3)
        assert q.is_sufficient is False

    def test_boundary_quality(self):
        q = ReviewQuality(quality_score=0.3, data_completeness=1.0, analysis_depth=1.0)
        assert q.is_sufficient is True

    def test_score_out_of_range_raises(self):
        with pytest.raises(ValueError, match="quality_score"):
            ReviewQuality(quality_score=1.5, data_completeness=1.0, analysis_depth=1.0)


# --- ReviewContextSnapshot Tests ---

class TestReviewContextSnapshot:
    def test_valid_snapshot(self):
        s = _make_snapshot()
        assert s.snapshot_hash == "abc123"

    def test_empty_evaluation_snapshot_raises(self):
        with pytest.raises(ValueError, match="evaluation_snapshot"):
            ReviewContextSnapshot(evaluation_snapshot={}, decision_snapshot={"id": "d1"}, snapshot_hash="h")

    def test_empty_hash_raises(self):
        with pytest.raises(ValueError, match="snapshot_hash"):
            ReviewContextSnapshot(evaluation_snapshot={"id": "e1"}, decision_snapshot={"id": "d1"}, snapshot_hash="")


# --- RecommendationImpact Tests ---

class TestRecommendationImpact:
    def test_valid_impact(self):
        i = RecommendationImpact(
            expected_return_bps=10.0,
            expected_risk_reduction_pct=5.0,
            implementation_cost_bps=2.0,
            confidence=0.7,
        )
        assert i.confidence == 0.7

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            RecommendationImpact(
                expected_return_bps=10.0,
                expected_risk_reduction_pct=5.0,
                implementation_cost_bps=2.0,
                confidence=1.5,
            )


# --- ReviewFinding Tests ---

class TestReviewFinding:
    def test_valid_finding(self):
        f = _make_finding()
        assert f.finding_id == "f1"
        assert f.dimension == "THESIS"

    def test_empty_finding_id_raises(self):
        with pytest.raises(InvalidFindingError, match="finding_id"):
            _make_finding(finding_id="")

    def test_empty_dimension_raises(self):
        with pytest.raises(InvalidFindingError, match="dimension"):
            _make_finding(dimension="")

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(InvalidFindingError, match="confidence"):
            _make_finding(confidence=1.5)

    def test_empty_description_raises(self):
        with pytest.raises(InvalidFindingError, match="description"):
            _make_finding(description="")

    def test_frozen(self):
        f = _make_finding()
        with pytest.raises(AttributeError):
            f.finding_id = "changed"


# --- ReviewRecommendation Tests ---

class TestReviewRecommendation:
    def test_valid_recommendation(self):
        r = _make_recommendation()
        assert r.recommendation_id == "r1"
        assert r.finding_id == "f1"

    def test_empty_recommendation_id_raises(self):
        with pytest.raises(InvalidRecommendationError, match="recommendation_id"):
            _make_recommendation(recommendation_id="")

    def test_empty_finding_id_raises(self):
        with pytest.raises(InvalidRecommendationError, match="finding_id"):
            _make_recommendation(finding_id="")

    def test_empty_description_raises(self):
        with pytest.raises(InvalidRecommendationError, match="description"):
            _make_recommendation(description="")

    def test_empty_expected_impact_raises(self):
        with pytest.raises(InvalidRecommendationError, match="expected_impact"):
            _make_recommendation(expected_impact="")

    def test_empty_implementation_risk_raises(self):
        with pytest.raises(InvalidRecommendationError, match="implementation_risk"):
            _make_recommendation(implementation_risk="")

    def test_frozen(self):
        r = _make_recommendation()
        with pytest.raises(AttributeError):
            r.recommendation_id = "changed"


# --- ReviewAssessment Tests ---

class TestReviewAssessment:
    def test_valid_assessment(self):
        a = _make_assessment()
        assert a.review_id == "rev-1"
        assert a.review_type == ReviewType.WORKER

    def test_empty_review_id_raises(self):
        with pytest.raises(InvalidReviewError, match="review_id"):
            _make_assessment(review_id="")

    def test_empty_evaluation_id_raises(self):
        with pytest.raises(InvalidReviewError, match="evaluation_id"):
            _make_assessment(evaluation_id="")

    def test_empty_target_urn_raises(self):
        with pytest.raises(InvalidReviewError, match="target_urn"):
            _make_assessment(target_urn="")

    def test_empty_decision_id_raises(self):
        with pytest.raises(InvalidReviewError, match="decision_id"):
            _make_assessment(decision_id="")

    def test_empty_reviewed_by_raises(self):
        with pytest.raises(InvalidReviewError, match="reviewed_by"):
            _make_assessment(reviewed_by="")

    def test_frozen(self):
        a = _make_assessment()
        with pytest.raises(AttributeError):
            a.review_id = "changed"

    def test_findings_preserved(self):
        a = _make_assessment()
        assert len(a.findings) == 1
        assert a.findings[0].finding_id == "f1"

    def test_recommendations_preserved(self):
        a = _make_assessment()
        assert len(a.recommendations) == 1
        assert a.recommendations[0].recommendation_id == "r1"


# --- Size Guardrail Tests (ADR-111) ---

class TestSizeGuardrail:
    def test_max_findings_allowed(self):
        findings = [_make_finding(finding_id=f"f{i}") for i in range(MAX_FINDINGS)]
        a = _make_assessment(findings=findings)
        assert len(a.findings) == MAX_FINDINGS

    def test_exceed_max_findings_raises(self):
        findings = [_make_finding(finding_id=f"f{i}") for i in range(MAX_FINDINGS + 1)]
        with pytest.raises(SizeGuardrailExceededError, match="Findings count"):
            _make_assessment(findings=findings)

    def test_max_recommendations_allowed(self):
        recs = [_make_recommendation(recommendation_id=f"r{i}") for i in range(MAX_RECOMMENDATIONS)]
        a = _make_assessment(recommendations=recs)
        assert len(a.recommendations) == MAX_RECOMMENDATIONS

    def test_exceed_max_recommendations_raises(self):
        recs = [_make_recommendation(recommendation_id=f"r{i}") for i in range(MAX_RECOMMENDATIONS + 1)]
        with pytest.raises(SizeGuardrailExceededError, match="Recommendations count"):
            _make_assessment(recommendations=recs)

    def test_empty_findings_allowed(self):
        a = _make_assessment(findings=[])
        assert len(a.findings) == 0

    def test_empty_recommendations_allowed(self):
        a = _make_assessment(recommendations=[])
        assert len(a.recommendations) == 0


# --- Immutability Tests ---

class TestImmutability:
    def test_cannot_modify_review_id(self):
        a = _make_assessment()
        with pytest.raises(AttributeError):
            a.review_id = "changed"

    def test_cannot_modify_findings(self):
        a = _make_assessment()
        with pytest.raises(AttributeError):
            a.findings = []

    def test_cannot_modify_recommendations(self):
        a = _make_assessment()
        with pytest.raises(AttributeError):
            a.recommendations = []

    def test_cannot_delete_field(self):
        a = _make_assessment()
        with pytest.raises(AttributeError):
            del a.review_id

    def test_finding_immutability(self):
        f = _make_finding()
        with pytest.raises(AttributeError):
            f.finding_id = "changed"

    def test_recommendation_immutability(self):
        r = _make_recommendation()
        with pytest.raises(AttributeError):
            r.recommendation_id = "changed"
