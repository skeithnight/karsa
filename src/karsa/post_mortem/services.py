from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

from karsa.post_mortem.models import PostMortemRecord, Recommendation
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding,
)
from karsa.post_mortem.repositories import PostMortemRecordRepository, RecommendationRepository
from karsa.post_mortem.ports import EventPublisherPort, SignatureValidationPort
from karsa.post_mortem.exceptions import ImmutabilityViolationException
from karsa.post_mortem.events import (
    PostMortemRecordCreatedEvent,
    RecommendationCreatedEvent,
    RecommendationAcceptedEvent,
    RecommendationRejectedEvent,
    RecommendationImplementedEvent,
    RecommendationExpiredEvent,
)

class PostMortemService:
    def __init__(self, record_repo: PostMortemRecordRepository, rec_repo: RecommendationRepository, publisher: EventPublisherPort):
        self.record_repo = record_repo
        self.rec_repo = rec_repo
        self.publisher = publisher

    def create_post_mortem(
        self,
        postmortem_id: str,
        incident_ref: IncidentReference,
        failure_classification: FailureClassification,
        root_causes: List[RootCauseContribution],
        findings: PostMortemFinding,
        created_at: datetime,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> PostMortemRecord:
        # Check uniqueness of incident_ref
        existing = self.record_repo.get_record_by_incident_ref(incident_ref.incident_ref)
        if existing:
            raise ImmutabilityViolationException(
                f"Incident reference {incident_ref.incident_ref} already has a post-mortem record."
            )

        # Create record (which will validate weights invariant)
        record = PostMortemRecord(
            postmortem_id=postmortem_id,
            incident_ref=incident_ref,
            failure_classification=failure_classification,
            root_causes=root_causes,
            findings=findings,
            created_at=created_at
        )

        self.record_repo.save_record(record)

        # Publish event
        event = PostMortemRecordCreatedEvent(
            event_id=f"evt_pm_{uuid.uuid4()}",
            correlation_id=correlation_id or postmortem_id,
            causation_id=causation_id or incident_ref.incident_ref,
            timestamp=datetime.utcnow(),
            postmortem_id=postmortem_id,
            incident_ref=incident_ref.incident_ref,
            failure_classification={
                "failure_type": failure_classification.failure_type,
                "severity": failure_classification.severity,
                "taxonomy_version": failure_classification.taxonomy_version
            },
            root_causes=[
                {
                    "cause_category": rc.cause_category,
                    "weight": rc.weight,
                    "description": rc.description
                } for rc in root_causes
            ],
            findings={
                "timeline_events": findings.timeline_events,
                "evidence_uris": findings.evidence_uris
            }
        )
        self.publisher.publish(event)
        return record

    def create_recommendation(
        self,
        recommendation_id: str,
        postmortem_id: str,
        target_context: str,
        action_item: str,
        parameters: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> Recommendation:
        # Verify post_mortem exists
        pm = self.record_repo.get_record_by_id(postmortem_id)
        if not pm:
            raise ValueError(f"Post-mortem record {postmortem_id} does not exist.")

        rec = Recommendation(
            recommendation_id=recommendation_id,
            postmortem_id=postmortem_id,
            target_context=target_context,
            action_item=action_item,
            parameters=parameters,
            state="PROPOSED",
            version=1,
            updated_at=datetime.utcnow()
        )

        self.rec_repo.save_recommendation(rec)

        # Publish event
        event = RecommendationCreatedEvent(
            event_id=f"evt_rec_{uuid.uuid4()}",
            correlation_id=correlation_id or postmortem_id,
            causation_id=causation_id or postmortem_id,
            timestamp=datetime.utcnow(),
            recommendation_id=recommendation_id,
            postmortem_id=postmortem_id,
            target_context=target_context,
            action_item=action_item,
            parameters=parameters
        )
        self.publisher.publish(event)
        return rec

class RecommendationRegistryService:
    def __init__(self, rec_repo: RecommendationRepository, publisher: EventPublisherPort, signature_validator: SignatureValidationPort):
        self.rec_repo = rec_repo
        self.publisher = publisher
        self.signature_validator = signature_validator

    def accept_recommendation(self, rec_id: str, signature: str, caller_payload: Dict[str, Any]) -> Recommendation:
        rec = self.rec_repo.get_recommendation_by_id(rec_id)
        if not rec:
            raise ValueError(f"Recommendation {rec_id} not found.")

        # Enforce target context authorization
        if not self.signature_validator.validate_signature(rec.target_context, signature, caller_payload):
            raise PermissionError(f"Caller is not authorized to accept recommendations for target context {rec.target_context}")

        rec.accept()
        self.rec_repo.save_recommendation(rec)

        # Publish event
        event = RecommendationAcceptedEvent(
            event_id=f"evt_rec_acc_{uuid.uuid4()}",
            correlation_id=rec.postmortem_id,
            causation_id=rec_id,
            timestamp=datetime.utcnow(),
            recommendation_id=rec_id,
            postmortem_id=rec.postmortem_id,
            target_context=rec.target_context
        )
        self.publisher.publish(event)
        return rec

    def reject_recommendation(self, rec_id: str, signature: str, caller_payload: Dict[str, Any]) -> Recommendation:
        rec = self.rec_repo.get_recommendation_by_id(rec_id)
        if not rec:
            raise ValueError(f"Recommendation {rec_id} not found.")

        # Enforce target context authorization
        if not self.signature_validator.validate_signature(rec.target_context, signature, caller_payload):
            raise PermissionError(f"Caller is not authorized to reject recommendations for target context {rec.target_context}")

        rec.reject()
        self.rec_repo.save_recommendation(rec)

        # Publish event
        event = RecommendationRejectedEvent(
            event_id=f"evt_rec_rej_{uuid.uuid4()}",
            correlation_id=rec.postmortem_id,
            causation_id=rec_id,
            timestamp=datetime.utcnow(),
            recommendation_id=rec_id,
            postmortem_id=rec.postmortem_id,
            target_context=rec.target_context
        )
        self.publisher.publish(event)
        return rec

    def implement_recommendation(self, rec_id: str, signature: str, caller_payload: Dict[str, Any]) -> Recommendation:
        rec = self.rec_repo.get_recommendation_by_id(rec_id)
        if not rec:
            raise ValueError(f"Recommendation {rec_id} not found.")

        # Enforce target context authorization
        if not self.signature_validator.validate_signature(rec.target_context, signature, caller_payload):
            raise PermissionError(f"Caller is not authorized to implement recommendations for target context {rec.target_context}")

        rec.implement()
        self.rec_repo.save_recommendation(rec)

        # Publish event
        event = RecommendationImplementedEvent(
            event_id=f"evt_rec_imp_{uuid.uuid4()}",
            correlation_id=rec.postmortem_id,
            causation_id=rec_id,
            timestamp=datetime.utcnow(),
            recommendation_id=rec_id,
            postmortem_id=rec.postmortem_id,
            target_context=rec.target_context
        )
        self.publisher.publish(event)
        return rec

    def expire_recommendation(self, rec_id: str) -> Recommendation:
        rec = self.rec_repo.get_recommendation_by_id(rec_id)
        if not rec:
            raise ValueError(f"Recommendation {rec_id} not found.")

        # No signature required for expire (Post-Mortem owns expiration)
        rec.expire()
        self.rec_repo.save_recommendation(rec)

        # Publish event
        event = RecommendationExpiredEvent(
            event_id=f"evt_rec_exp_{uuid.uuid4()}",
            correlation_id=rec.postmortem_id,
            causation_id=rec_id,
            timestamp=datetime.utcnow(),
            recommendation_id=rec_id,
            postmortem_id=rec.postmortem_id,
            target_context=rec.target_context
        )
        self.publisher.publish(event)
        return rec
