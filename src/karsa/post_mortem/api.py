from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

from karsa.post_mortem.services import PostMortemService, RecommendationRegistryService
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding,
)
from karsa.post_mortem.exceptions import (
    AttributionWeightException,
    RecommendationStateConflictException,
    ImmutabilityViolationException,
)
from karsa.shared.infrastructure.uow import ConcurrencyConflictError

router = APIRouter(prefix="/post-mortem", tags=["Post-Mortem Engine"])

_post_mortem_service: Optional[PostMortemService] = None
_recommendation_registry_service: Optional[RecommendationRegistryService] = None

def get_post_mortem_service() -> PostMortemService:
    if _post_mortem_service is None:
        raise RuntimeError("PostMortemService not configured for API.")
    return _post_mortem_service

def get_recommendation_registry_service() -> RecommendationRegistryService:
    if _recommendation_registry_service is None:
        raise RuntimeError("RecommendationRegistryService not configured for API.")
    return _recommendation_registry_service

def configure_api(pm_service: PostMortemService, rec_service: RecommendationRegistryService):
    global _post_mortem_service, _recommendation_registry_service
    _post_mortem_service = pm_service
    _recommendation_registry_service = rec_service

class FailureClassificationSchema(BaseModel):
    failure_type: str
    severity: str
    taxonomy_version: int = 1

class RootCauseContributionSchema(BaseModel):
    cause_category: str
    weight: float
    description: str

class PostMortemFindingSchema(BaseModel):
    timeline_events: List[Dict[str, Any]]
    evidence_uris: List[str]

class PostMortemCreateRequest(BaseModel):
    postmortem_id: str
    incident_ref: str
    failure_classification: FailureClassificationSchema
    root_causes: List[RootCauseContributionSchema]
    findings: PostMortemFindingSchema
    created_at: Optional[datetime] = None

class RecommendationCreateRequest(BaseModel):
    recommendation_id: str
    postmortem_id: str
    target_context: str
    action_item: str
    parameters: Dict[str, Any]

class RecommendationTransitionRequest(BaseModel):
    signature: str
    caller_payload: Dict[str, Any]

@router.post("/records", status_code=status.HTTP_201_CREATED)
def create_post_mortem(
    request: PostMortemCreateRequest,
    service: PostMortemService = Depends(get_post_mortem_service)
):
    try:
        incident_ref = IncidentReference(request.incident_ref)
        failure_classification = FailureClassification(
            failure_type=request.failure_classification.failure_type,
            severity=request.failure_classification.severity,
            taxonomy_version=request.failure_classification.taxonomy_version
        )
        root_causes = [
            RootCauseContribution(
                cause_category=rc.cause_category,
                weight=rc.weight,
                description=rc.description
            ) for rc in request.root_causes
        ]
        findings = PostMortemFinding(
            timeline_events=request.findings.timeline_events,
            evidence_uris=request.findings.evidence_uris
        )
        created_at = request.created_at or datetime.utcnow()

        record = service.create_post_mortem(
            postmortem_id=request.postmortem_id,
            incident_ref=incident_ref,
            failure_classification=failure_classification,
            root_causes=root_causes,
            findings=findings,
            created_at=created_at
        )

        return {
            "postmortem_id": record.postmortem_id,
            "incident_ref": record.incident_ref.incident_ref,
            "created_at": record.created_at.isoformat()
        }
    except AttributionWeightException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ImmutabilityViolationException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/records/{postmortem_id}")
def get_post_mortem(
    postmortem_id: str,
    service: PostMortemService = Depends(get_post_mortem_service)
):
    record = service.record_repo.get_record_by_id(postmortem_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post-mortem record {postmortem_id} not found.")
    
    return {
        "postmortem_id": record.postmortem_id,
        "incident_ref": record.incident_ref.incident_ref,
        "failure_classification": {
            "failure_type": record.failure_classification.failure_type,
            "severity": record.failure_classification.severity,
            "taxonomy_version": record.failure_classification.taxonomy_version
        },
        "root_causes": [
            {
                "cause_category": rc.cause_category,
                "weight": rc.weight,
                "description": rc.description
            } for rc in record.root_causes
        ],
        "findings": {
            "timeline_events": record.findings.timeline_events,
            "evidence_uris": record.findings.evidence_uris
        },
        "created_at": record.created_at.isoformat()
    }

@router.post("/recommendations", status_code=status.HTTP_201_CREATED)
def create_recommendation(
    request: RecommendationCreateRequest,
    service: PostMortemService = Depends(get_post_mortem_service)
):
    try:
        rec = service.create_recommendation(
            recommendation_id=request.recommendation_id,
            postmortem_id=request.postmortem_id,
            target_context=request.target_context,
            action_item=request.action_item,
            parameters=request.parameters
        )
        return {
            "recommendation_id": rec.recommendation_id,
            "postmortem_id": rec.postmortem_id,
            "target_context": rec.target_context,
            "state": rec.state,
            "version": rec.version
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/recommendations/{recommendation_id}")
def get_recommendation(
    recommendation_id: str,
    service: PostMortemService = Depends(get_post_mortem_service)
):
    rec = service.rec_repo.get_recommendation_by_id(recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recommendation {recommendation_id} not found.")
    
    return {
        "recommendation_id": rec.recommendation_id,
        "postmortem_id": rec.postmortem_id,
        "target_context": rec.target_context,
        "action_item": rec.action_item,
        "parameters": rec.parameters,
        "state": rec.state,
        "version": rec.version,
        "updated_at": rec.updated_at.isoformat()
    }

@router.post("/recommendations/{recommendation_id}/accept")
def accept_recommendation(
    recommendation_id: str,
    request: RecommendationTransitionRequest,
    service: RecommendationRegistryService = Depends(get_recommendation_registry_service)
):
    try:
        rec = service.accept_recommendation(
            rec_id=recommendation_id,
            signature=request.signature,
            caller_payload=request.caller_payload
        )
        return {
            "recommendation_id": rec.recommendation_id,
            "state": rec.state,
            "version": rec.version
        }
    except RecommendationStateConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/recommendations/{recommendation_id}/reject")
def reject_recommendation(
    recommendation_id: str,
    request: RecommendationTransitionRequest,
    service: RecommendationRegistryService = Depends(get_recommendation_registry_service)
):
    try:
        rec = service.reject_recommendation(
            rec_id=recommendation_id,
            signature=request.signature,
            caller_payload=request.caller_payload
        )
        return {
            "recommendation_id": rec.recommendation_id,
            "state": rec.state,
            "version": rec.version
        }
    except RecommendationStateConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/recommendations/{recommendation_id}/implement")
def implement_recommendation(
    recommendation_id: str,
    request: RecommendationTransitionRequest,
    service: RecommendationRegistryService = Depends(get_recommendation_registry_service)
):
    try:
        rec = service.implement_recommendation(
            rec_id=recommendation_id,
            signature=request.signature,
            caller_payload=request.caller_payload
        )
        return {
            "recommendation_id": rec.recommendation_id,
            "state": rec.state,
            "version": rec.version
        }
    except RecommendationStateConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/recommendations/{recommendation_id}/expire")
def expire_recommendation(
    recommendation_id: str,
    service: RecommendationRegistryService = Depends(get_recommendation_registry_service)
):
    try:
        rec = service.expire_recommendation(rec_id=recommendation_id)
        return {
            "recommendation_id": rec.recommendation_id,
            "state": rec.state,
            "version": rec.version
        }
    except RecommendationStateConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
