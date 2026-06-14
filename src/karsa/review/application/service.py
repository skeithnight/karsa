import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from decimal import Decimal

from karsa.review.domain.model.review import ReviewSession, LearningFeedback
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
from karsa.review.domain.model.repositories import (
    ReviewSessionRepository,
    LearningFeedbackRepository
)
from karsa.review.events.events import (
    ReviewVerdictReachedEvent,
    FeedbackAppliedEvent,
    ResearchRecommendationProposedEvent
)

class LearningFeedbackService:
    def __init__(self, feedback_repo: LearningFeedbackRepository, events_list: Optional[List[Any]] = None):
        self.feedback_repo = feedback_repo
        self.events_list = events_list if events_list is not None else []

    def propose_feedback(
        self,
        session_id: str,
        target: ReviewTarget,
        category: LearningFeedbackCategory,
        suggested_action: str,
        parameters: Dict[str, Any]
    ) -> LearningFeedback:
        feedback = LearningFeedback(
            feedback_id=str(uuid.uuid4()),
            session_id=session_id,
            target=target,
            category=category,
            suggested_action=suggested_action,
            parameters=parameters,
            status="PROPOSED",
            created_at=datetime.utcnow(),
            aggregate_version=1
        )
        self.feedback_repo.save(feedback)
        
        # If the category is RESEARCH, we emit the ResearchRecommendationProposedEvent
        if category == LearningFeedbackCategory.RESEARCH:
            self.events_list.append(ResearchRecommendationProposedEvent(
                event_id=str(uuid.uuid4()),
                feedback_id=feedback.feedback_id,
                target_type=target.target_type.value,
                target_id=target.target_id,
                target_version=target.target_version or "",
                action=suggested_action,
                parameters=parameters,
                timestamp=datetime.utcnow()
            ))
        return feedback

    def accept_feedback(self, feedback_id: str) -> None:
        feedback = self.feedback_repo.find_by_id(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback not found: {feedback_id}")
        
        next_ver = feedback.aggregate_version + 1
        # Re-initialize to status ACCEPTED using accept() method
        feedback.accept()
        feedback.aggregate_version = next_ver
        self.feedback_repo.save(feedback)

    def reject_feedback(self, feedback_id: str) -> None:
        feedback = self.feedback_repo.find_by_id(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback not found: {feedback_id}")
        
        next_ver = feedback.aggregate_version + 1
        feedback.reject()
        feedback.aggregate_version = next_ver
        self.feedback_repo.save(feedback)

    def handle_feedback_applied(self, event: FeedbackAppliedEvent) -> None:
        feedback = self.feedback_repo.find_by_id(event.feedback_id)
        if not feedback:
            # Idempotency / replay safety: ignore if not found or already applied
            return
        
        if feedback.status == "APPLIED":
            return
            
        next_ver = feedback.aggregate_version + 1
        # Move feedback state to applied
        if feedback.status == "PROPOSED":
            feedback.accept() # Auto accept before applying if not already done
        feedback.apply(event.applied_at)
        feedback.aggregate_version = next_ver
        self.feedback_repo.save(feedback)


class ReviewService:
    def __init__(
        self,
        session_repo: ReviewSessionRepository,
        feedback_service: LearningFeedbackService,
        events_list: Optional[List[Any]] = None
    ):
        self.session_repo = session_repo
        self.feedback_service = feedback_service
        self.events_list = events_list if events_list is not None else []

    def start_review_session(
        self,
        target_type: str,
        target_id: str,
        session_type: str,
        target_version: Optional[str] = None,
        regime_id: Optional[str] = None
    ) -> ReviewSession:
        target = ReviewTarget(
            target_type=ReviewTargetType(target_type),
            target_id=target_id,
            target_version=target_version
        )
        session = ReviewSession(
            session_id=str(uuid.uuid4()),
            target=target,
            session_type=ReviewSessionType(session_type),
            status="CREATED",
            regime_id=regime_id,
            created_at=datetime.utcnow(),
            aggregate_version=1
        )
        session.start_session()
        self.session_repo.save(session)
        return session

    def register_finding(
        self,
        session_id: str,
        finding_type: str,
        severity: str,
        description: str
    ) -> None:
        session = self.session_repo.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
            
        finding = ReviewFinding(
            finding_id=str(uuid.uuid4()),
            finding_type=finding_type,
            severity=severity,
            description=description,
            created_at=datetime.utcnow()
        )
        next_ver = session.aggregate_version + 1
        session.add_finding(finding)
        session.aggregate_version = next_ver
        self.session_repo.save(session)

    def register_evidence(
        self,
        session_id: str,
        source_type: str,
        source_reference_id: str,
        evidence_summary: str,
        retention_class: str,
        llm_config: Optional[LLMConfigSnapshot] = None
    ) -> None:
        session = self.session_repo.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Compute SHA-256 checksum over the raw summary to verify evidence integrity
        evidence_hash = hashlib.sha256(evidence_summary.encode("utf-8")).hexdigest()

        evidence = ReviewEvidence(
            evidence_id=str(uuid.uuid4()),
            source_type=source_type,
            source_reference_id=source_reference_id,
            evidence_hash=evidence_hash,
            evidence_summary=evidence_summary,
            retention_class=EvidenceRetentionClass(retention_class),
            created_at=datetime.utcnow(),
            llm_config=llm_config
        )
        next_ver = session.aggregate_version + 1
        session.add_evidence(evidence)
        session.aggregate_version = next_ver
        self.session_repo.save(session)

    def complete_review_session(
        self,
        session_id: str,
        outcome_rating: str,
        justification: str
    ) -> ReviewSession:
        session = self.session_repo.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        verdict = ReviewVerdict(
            verdict_id=str(uuid.uuid4()),
            outcome_rating=ReviewVerdictOutcome(outcome_rating),
            justification=justification,
            created_at=datetime.utcnow()
        )
        
        next_ver = session.aggregate_version + 1
        session.complete_session(verdict)
        session.aggregate_version = next_ver
        self.session_repo.save(session)

        # Emit ReviewVerdictReachedEvent
        self.events_list.append(ReviewVerdictReachedEvent(
            event_id=str(uuid.uuid4()),
            session_id=session.session_id,
            session_type=session.session_type.value,
            target_type=session.target.target_type.value,
            target_id=session.target.target_id,
            target_version=session.target.target_version or "",
            regime_id=session.regime_id or "",
            correlation_ids=[e.source_reference_id for e in session.evidence],
            verdict_id=verdict.verdict_id,
            outcome_rating=verdict.outcome_rating.value,
            justification=verdict.justification,
            timestamp=datetime.utcnow()
        ))
        
        # If verdict is a critical failure, propose learning feedback automatically
        if verdict.outcome_rating in (ReviewVerdictOutcome.CRITICAL_DEPRECATE, ReviewVerdictOutcome.SUSPEND_RECALIBRATE):
            category = LearningFeedbackCategory.THESIS
            action = "INVALIDATE_VERSION"
            if session.target.target_type == ReviewTargetType.WORKER:
                category = LearningFeedbackCategory.WORKER
                action = "SUSPEND_PROVIDER"
            elif session.target.target_type == ReviewTargetType.PORTFOLIO:
                category = LearningFeedbackCategory.CAPITAL
                action = "HALT_FUNDING"
                
            self.feedback_service.propose_feedback(
                session_id=session.session_id,
                target=session.target,
                category=category,
                suggested_action=action,
                parameters={
                    "justification": verdict.justification,
                    "severity": "CRITICAL"
                }
            )

        return session
