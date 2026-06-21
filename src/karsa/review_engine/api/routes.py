"""Review Engine API Routes — Sprint-10 Wave-7.

Read-only API layer. No write endpoints.
Writes occur only through ReviewExecutionService.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from karsa.review_engine.infrastructure.repositories.review_assessment_repository import ReviewAssessmentRepository
from karsa.review_engine.infrastructure.repositories.review_projection_repository import ReviewProjectionRepository
from karsa.review_engine.infrastructure.persistence.postgres_review_assessment_repository import PostgresReviewAssessmentRepository
from karsa.review_engine.infrastructure.persistence.postgres_review_projection_repository import PostgresReviewProjectionRepository

router = APIRouter(prefix="/api/v1/reviews", tags=["Reviews"])


# --- Dependency injection placeholders ---

_assessment_repo: Optional[ReviewAssessmentRepository] = None
_projection_repo: Optional[ReviewProjectionRepository] = None


def init_routes(app, assessment_repo: ReviewAssessmentRepository, projection_repo: ReviewProjectionRepository):
    """Initialize routes with repository dependencies."""
    global _assessment_repo, _projection_repo
    _assessment_repo = assessment_repo
    _projection_repo = projection_repo
    app.include_router(router)


# --- Endpoint 1: Get review by ID ---

@router.get("/{review_id}")
def get_review(review_id: str):
    """Get a review assessment by ID."""
    if not _assessment_repo:
        raise HTTPException(status_code=500, detail="Service not initialized")

    review = _assessment_repo.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    return {
        "review_id": review.review_id,
        "evaluation_id": review.evaluation_id,
        "review_type": review.review_type.value,
        "review_version": review.review_version,
        "target_urn": review.target_urn,
        "findings": review.findings,
        "recommendations": review.recommendations,
        "review_summary": review.review_summary,
        "review_quality": review.review_quality,
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
    }


# --- Endpoint 2: List reviews ---

@router.get("")
def list_reviews(
    evaluation_id: Optional[str] = Query(None),
    review_type: Optional[str] = Query(None),
    target_urn: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
):
    """List reviews with filters and pagination."""
    if not _assessment_repo:
        raise HTTPException(status_code=500, detail="Service not initialized")

    reviews = _assessment_repo.list_reviews(page=page, size=size)

    items = []
    for r in reviews:
        if evaluation_id and r.evaluation_id != evaluation_id:
            continue
        if review_type and r.review_type.value != review_type:
            continue
        if target_urn and r.target_urn != target_urn:
            continue
        items.append({
            "review_id": r.review_id,
            "evaluation_id": r.evaluation_id,
            "review_type": r.review_type.value,
            "review_version": r.review_version,
            "target_urn": r.target_urn,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        })

    return {
        "data": items,
        "pagination": {
            "page": page,
            "size": size,
            "total_items": len(items),
            "total_pages": 1,
        }
    }


# --- Endpoint 3: Worker review ---

@router.get("/workers/{target_urn}")
def get_worker_review(target_urn: str):
    """Get worker review projection."""
    if not _projection_repo:
        raise HTTPException(status_code=500, detail="Service not initialized")

    review = _projection_repo.get_worker_review(target_urn)
    if not review:
        raise HTTPException(status_code=404, detail=f"Worker review for {target_urn} not found")

    return {
        "target_urn": review["target_urn"],
        "total_reviews": review["total_reviews"],
        "avg_quality_score": float(review["avg_quality_score"]),
        "total_findings": review["total_findings"],
        "total_recommendations": review["total_recommendations"],
        "last_reviewed": review["last_reviewed"],
    }


# --- Endpoint 4: Thesis review ---

@router.get("/theses/{thesis_urn}")
def get_thesis_review(thesis_urn: str):
    """Get thesis review projection."""
    if not _projection_repo:
        raise HTTPException(status_code=500, detail="Service not initialized")

    review = _projection_repo.get_thesis_review(thesis_urn)
    if not review:
        raise HTTPException(status_code=404, detail=f"Thesis review for {thesis_urn} not found")

    return {
        "thesis_urn": review["thesis_urn"],
        "total_reviews": review["total_reviews"],
        "avg_quality_score": float(review["avg_quality_score"]),
        "last_reviewed": review["last_reviewed"],
    }


# --- Endpoint 5: Capability gaps ---

@router.get("/capability-gaps/{target_urn}")
def get_capability_gaps(target_urn: str):
    """Get capability gap projections."""
    if not _projection_repo:
        raise HTTPException(status_code=500, detail="Service not initialized")

    gaps = _projection_repo.get_capability_gaps(target_urn)
    return {
        "target_urn": target_urn,
        "gaps": gaps,
        "total_gaps": len(gaps),
    }


# --- Endpoint 6: Coverage ---

@router.get("/coverage/{evaluation_id}")
def get_coverage(evaluation_id: str):
    """Get review coverage for an evaluation."""
    if not _projection_repo:
        raise HTTPException(status_code=500, detail="Service not initialized")

    coverage = _projection_repo.get_review_coverage(evaluation_id)
    if not coverage:
        raise HTTPException(status_code=404, detail=f"Coverage for {evaluation_id} not found")

    return {
        "decision_id": coverage.get("decision_id"),
        "proposal_id": coverage.get("proposal_id"),
        "review_type": coverage.get("review_type"),
        "review_status": coverage.get("review_status"),
        "review_id": coverage.get("review_id"),
        "review_due_date": coverage.get("review_due_date"),
        "executed_at": coverage.get("executed_at"),
        "days_overdue": coverage.get("days_overdue"),
    }
