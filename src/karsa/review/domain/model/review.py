import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.review.domain.model.value_objects import (
    ReviewTarget,
    ReviewTargetType,
    ReviewSessionType,
    ReviewVerdictOutcome,
    LearningFeedbackCategory,
    EvidenceRetentionClass,
    ReviewEvidence,
    ReviewFinding,
    ReviewVerdict,
    LLMConfigSnapshot
)

class ReviewSession(VersionedAggregate):
    def __init__(
        self,
        session_id: str,
        target: ReviewTarget,
        session_type: ReviewSessionType,
        findings: Optional[List[ReviewFinding]] = None,
        evidence: Optional[List[ReviewEvidence]] = None,
        verdict: Optional[ReviewVerdict] = None,
        status: str = "CREATED",
        regime_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.session_id = session_id
        self.target = target
        self.session_type = session_type
        self.findings = findings or []
        self.evidence = evidence or []
        self.verdict = verdict
        self.status = status
        self.regime_id = regime_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if self.status in ("COMPLETED", "ABANDONED") and name != "aggregate_version":
                raise TypeError("Cannot modify immutable ReviewSession aggregate after completion/abandonment")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            if self.status in ("COMPLETED", "ABANDONED"):
                raise TypeError("Cannot modify immutable ReviewSession aggregate after completion/abandonment")
        super().__delattr__(name)

    def start_session(self) -> None:
        if self.status != "CREATED":
            raise ValueError(f"Cannot start review session in status: {self.status}")
        self.status = "IN_PROGRESS"
        self.updated_at = datetime.utcnow()

    def add_finding(self, finding: ReviewFinding) -> None:
        if self.status != "IN_PROGRESS":
            raise ValueError("Can only add findings to an in-progress review session")
        self.findings.append(finding)
        self.updated_at = datetime.utcnow()

    def add_evidence(self, ev: ReviewEvidence) -> None:
        if self.status != "IN_PROGRESS":
            raise ValueError("Can only add evidence to an in-progress review session")
        self.evidence.append(ev)
        self.updated_at = datetime.utcnow()

    def complete_session(self, verdict: ReviewVerdict) -> None:
        if self.status != "IN_PROGRESS":
            raise ValueError("Can only complete an in-progress review session")
        self.verdict = verdict
        self.updated_at = datetime.utcnow()
        self.status = "COMPLETED"

    def abandon_session(self) -> None:
        if self.status != "IN_PROGRESS":
            raise ValueError("Can only abandon an in-progress review session")
        self.updated_at = datetime.utcnow()
        self.status = "ABANDONED"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "target": {
                "target_type": self.target.target_type.value,
                "target_id": self.target.target_id,
                "target_version": self.target.target_version
            },
            "session_type": self.session_type.value,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "description": f.description,
                    "created_at": f.created_at.isoformat()
                } for f in self.findings
            ],
            "evidence": [
                {
                    "evidence_id": ev.evidence_id,
                    "source_type": ev.source_type,
                    "source_reference_id": ev.source_reference_id,
                    "evidence_hash": ev.evidence_hash,
                    "evidence_summary": ev.evidence_summary,
                    "retention_class": ev.retention_class.value,
                    "created_at": ev.created_at.isoformat(),
                    "llm_config": {
                        "model_name": ev.llm_config.model_name,
                        "temperature": str(ev.llm_config.temperature),
                        "seed": ev.llm_config.seed
                    } if ev.llm_config else None
                } for ev in self.evidence
            ],
            "verdict": {
                "verdict_id": self.verdict.verdict_id,
                "outcome_rating": self.verdict.outcome_rating.value,
                "justification": self.verdict.justification,
                "created_at": self.verdict.created_at.isoformat()
            } if self.verdict else None,
            "status": self.status,
            "regime_id": self.regime_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ReviewSession':
        target = ReviewTarget(
            target_type=ReviewTargetType(data["target"]["target_type"]),
            target_id=data["target"]["target_id"],
            target_version=data["target"].get("target_version")
        )
        session_type = ReviewSessionType(data["session_type"])
        findings = [
            ReviewFinding(
                finding_id=f["finding_id"],
                finding_type=f["finding_type"],
                severity=f["severity"],
                description=f["description"],
                created_at=datetime.fromisoformat(f["created_at"])
            ) for f in data["findings"]
        ]
        evidence = []
        for ev in data["evidence"]:
            llm_config = None
            if ev.get("llm_config"):
                llm_config = LLMConfigSnapshot(
                    model_name=ev["llm_config"]["model_name"],
                    temperature=Decimal(ev["llm_config"]["temperature"]),
                    seed=ev["llm_config"]["seed"]
                )
            evidence.append(ReviewEvidence(
                evidence_id=ev["evidence_id"],
                source_type=ev["source_type"],
                source_reference_id=ev["source_reference_id"],
                evidence_hash=ev["evidence_hash"],
                evidence_summary=ev["evidence_summary"],
                retention_class=EvidenceRetentionClass(ev["retention_class"]),
                created_at=datetime.fromisoformat(ev["created_at"]),
                llm_config=llm_config
            ))

        verdict = None
        if data.get("verdict"):
            verdict = ReviewVerdict(
                verdict_id=data["verdict"]["verdict_id"],
                outcome_rating=ReviewVerdictOutcome(data["verdict"]["outcome_rating"]),
                justification=data["verdict"]["justification"],
                created_at=datetime.fromisoformat(data["verdict"]["created_at"])
            )

        return cls(
            session_id=data["session_id"],
            target=target,
            session_type=session_type,
            findings=findings,
            evidence=evidence,
            verdict=verdict,
            status=data["status"],
            regime_id=data.get("regime_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            aggregate_version=data.get("aggregate_version", 1)
        )


class LearningFeedback(VersionedAggregate):
    def __init__(
        self,
        feedback_id: str,
        session_id: str,
        target: ReviewTarget,
        category: LearningFeedbackCategory,
        suggested_action: str,
        parameters: Dict[str, Any],
        status: str = "PROPOSED",
        created_at: Optional[datetime] = None,
        applied_at: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.feedback_id = feedback_id
        self.session_id = session_id
        self.target = target
        self.category = category
        self.suggested_action = suggested_action
        self.parameters = parameters
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.applied_at = applied_at
        self._initialized = True

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            # The feedback is immutable once in applied/rejected state
            if self.status in ("APPLIED", "REJECTED") and name not in ("status", "applied_at", "aggregate_version"):
                raise TypeError("Cannot modify immutable LearningFeedback aggregate in finalized state")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            if self.status in ("APPLIED", "REJECTED"):
                raise TypeError("Cannot modify immutable LearningFeedback aggregate in finalized state")
        super().__delattr__(name)

    def accept(self) -> None:
        if self.status != "PROPOSED":
            raise ValueError(f"Cannot accept feedback in status: {self.status}")
        self.status = "ACCEPTED"

    def reject(self) -> None:
        if self.status != "PROPOSED":
            raise ValueError(f"Cannot reject feedback in status: {self.status}")
        self.status = "REJECTED"

    def apply(self, applied_at: datetime) -> None:
        if self.status != "ACCEPTED":
            raise ValueError("Can only apply feedback that has been accepted")
        self.applied_at = applied_at
        self.status = "APPLIED"

    def to_dict(self) -> dict:
        return {
            "feedback_id": self.feedback_id,
            "session_id": self.session_id,
            "target": {
                "target_type": self.target.target_type.value,
                "target_id": self.target.target_id,
                "target_version": self.target.target_version
            },
            "category": self.category.value,
            "suggested_action": self.suggested_action,
            "parameters": self.parameters,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LearningFeedback':
        target = ReviewTarget(
            target_type=ReviewTargetType(data["target"]["target_type"]),
            target_id=data["target"]["target_id"],
            target_version=data["target"].get("target_version")
        )
        category = LearningFeedbackCategory(data["category"])
        applied_at = datetime.fromisoformat(data["applied_at"]) if data.get("applied_at") else None
        return cls(
            feedback_id=data["feedback_id"],
            session_id=data["session_id"],
            target=target,
            category=category,
            suggested_action=data["suggested_action"],
            parameters=data["parameters"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            applied_at=applied_at,
            aggregate_version=data.get("aggregate_version", 1)
        )
