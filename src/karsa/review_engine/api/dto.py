"""Review Engine DTOs — Sprint-10 Wave-7.

All DTOs immutable. No persistence logic.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# --- Pagination ---

@dataclass(frozen=True)
class PaginationDTO:
    page: int
    size: int
    total_items: int
    total_pages: int


# --- Error ---

@dataclass(frozen=True)
class ErrorDetailDTO:
    code: str
    message: str


@dataclass(frozen=True)
class ErrorResponseDTO:
    error: ErrorDetailDTO


# --- Worker Review ---

@dataclass(frozen=True)
class WorkerReviewDTO:
    target_urn: str
    total_reviews: int
    avg_quality_score: float
    total_findings: int
    total_recommendations: int
    last_reviewed: Optional[str]  # ISO datetime


# --- Thesis Review ---

@dataclass(frozen=True)
class ThesisReviewDTO:
    thesis_urn: str
    total_reviews: int
    avg_quality_score: float
    last_reviewed: Optional[str]  # ISO datetime


# --- Capability Gap ---

@dataclass(frozen=True)
class CapabilityGapDTO:
    target_urn: str
    gap_type: str
    severity: str
    description: str
    identified_at: Optional[str]  # ISO datetime


# --- Review Coverage ---

@dataclass(frozen=True)
class ReviewCoverageDTO:
    decision_id: str
    proposal_id: Optional[str]
    cycle_id: Optional[str]
    review_type: Optional[str]
    review_status: str
    review_id: Optional[str]
    review_due_date: Optional[str]  # ISO datetime
    executed_at: Optional[str]  # ISO datetime
    days_overdue: Optional[int]


# --- Review Summary ---

@dataclass(frozen=True)
class ReviewSummaryDTO:
    review_id: str
    evaluation_id: str
    review_type: str
    review_version: str
    target_urn: str
    reviewed_at: Optional[str]  # ISO datetime


# --- Review Detail ---

@dataclass(frozen=True)
class ReviewDetailDTO:
    review_id: str
    evaluation_id: str
    review_type: str
    review_version: str
    target_urn: str
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    review_summary: Dict[str, Any]
    review_quality: Dict[str, Any]
    reviewed_at: Optional[str]  # ISO datetime
