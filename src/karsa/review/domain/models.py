from dataclasses import dataclass, field
from typing import List, Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.review.domain.events import (
    ReviewInitiatedEvent, EvidenceAttachedEvent, CalibrationGradedEvent, ReviewSealedEvent
)

@dataclass
class ReviewTarget:
    target_type: str
    target_urn: str

@dataclass
class EvidenceReference:
    source_type: str
    source_urn: str
    snapshot_version: int
    fingerprint_sha256: str

@dataclass
class ReviewLineage:
    parent_review_urn: Optional[str]
    supersedes_review_urn: Optional[str]
    lineage_type: str

@dataclass
class CalibrationGrade:
    stated_confidence: float
    actual_accuracy: float
    delta: float

class ReviewAssessment(VersionedAggregate):
    def __init__(self, aggregate_version: int = 1):
        super().__init__(aggregate_version)
        self.review_urn: str = ""
        self.target: Optional[ReviewTarget] = None
        self.state: str = "PENDING"
        self.evidence: List[EvidenceReference] = []
        self.calibration: Optional[CalibrationGrade] = None

    @property
    def aggregate_id(self) -> str:
        return self.review_urn

    @classmethod
    def initiate(cls, review_urn: str, target: ReviewTarget) -> "ReviewAssessment":
        review = cls(aggregate_version=1)
        review.review_urn = review_urn
        review.target = target
        
        event = ReviewInitiatedEvent(
            review_urn=review_urn,
            target_type=target.target_type,
            target_urn=target.target_urn
        )
        review.record_event(event)
        return review

    def attach_evidence(self, ev: EvidenceReference):
        if self.state == "SEALED":
            raise ValueError("Cannot attach evidence to sealed review")
        
        self.evidence.append(ev)
        event = EvidenceAttachedEvent(
            review_urn=self.review_urn,
            source_type=ev.source_type,
            source_urn=ev.source_urn,
            snapshot_version=ev.snapshot_version,
            fingerprint_sha256=ev.fingerprint_sha256
        )
        self.record_event(event)

    def grade_calibration(self, stated: float, actual: float, rationale: str):
        if self.state == "SEALED":
            raise ValueError("Cannot grade sealed review")
        
        self.calibration = CalibrationGrade(stated, actual, stated - actual)
        event = CalibrationGradedEvent(
            review_urn=self.review_urn,
            calibration_score=self.calibration.delta,
            rationale=rationale
        )
        self.record_event(event)

    def seal(self, accuracy: float, lineage: ReviewLineage):
        if not self.target:
            raise ValueError("Missing review target")
        if not self.evidence:
            raise ValueError("Missing cryptographic evidence")
        if not self.calibration:
            raise ValueError("Missing calibration grade")
        
        self.state = "SEALED"
        event = ReviewSealedEvent(
            review_urn=self.review_urn,
            target_type=self.target.target_type,
            target_urn=self.target.target_urn,
            accuracy=accuracy,
            parent_review_urn=lineage.parent_review_urn,
            supersedes_review_urn=lineage.supersedes_review_urn,
            lineage_type=lineage.lineage_type
        )
        self.record_event(event)

    def apply_event(self, event):
        if isinstance(event, ReviewInitiatedEvent):
            self.review_urn = event.payload["review_urn"]
            self.target = ReviewTarget(event.payload["target_type"], event.payload["target_urn"])
        elif isinstance(event, EvidenceAttachedEvent):
            self.evidence.append(EvidenceReference(
                event.payload["source_type"],
                event.payload["source_urn"],
                event.payload["snapshot_version"],
                event.payload["fingerprint_sha256"]
            ))
        elif isinstance(event, CalibrationGradedEvent):
            self.calibration = CalibrationGrade(0, 0, event.payload["calibration_score"])
        elif isinstance(event, ReviewSealedEvent):
            self.state = "SEALED"
        self.increment_version()
