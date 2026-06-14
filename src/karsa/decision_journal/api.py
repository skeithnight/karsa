from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from karsa.decision_journal.services import DecisionJournalService, JournalLineageResolver, ReplayService
from karsa.decision_journal.value_objects import (
    PromptReference, DatasetReference, TelemetryReference, ArtifactReference, ReplayMetadata, DecisionContextSnapshot, DecisionEvidence
)
from karsa.decision_journal.exceptions import DecisionJournalException, HindsightValidationException, LineageIntegrityException, VerificationFailedException

router = APIRouter(prefix="/journals", tags=["Decision Journal"])

# Dependency containers to be overridden/injected
_service: Optional[DecisionJournalService] = None
_resolver: Optional[JournalLineageResolver] = None
_replay: Optional[ReplayService] = None

def get_service() -> DecisionJournalService:
    if _service is None:
        raise RuntimeError("DecisionJournalService not configured for API.")
    return _service

def get_resolver() -> JournalLineageResolver:
    if _resolver is None:
        raise RuntimeError("JournalLineageResolver not configured for API.")
    return _resolver

def get_replay() -> ReplayService:
    if _replay is None:
        raise RuntimeError("ReplayService not configured for API.")
    return _replay

# Request Schemas
class PromptRefSchema(BaseModel):
    prompt_id: str
    prompt_hash: str
    template_urn: str

class DatasetRefSchema(BaseModel):
    dataset_id: str
    dataset_hash: str
    dataset_urn: str

class TelemetryRefSchema(BaseModel):
    telemetry_id: str
    telemetry_hash: str
    span_id: str

class ArtifactRefSchema(BaseModel):
    artifact_id: str
    artifact_hash: str
    artifact_urn: str

class ReplayMetadataSchema(BaseModel):
    git_commit: str
    runtime_image: str
    seed: Optional[int] = None
    temperature: Optional[float] = None
    regime_identifier: Optional[str] = None
    prompt_hash: Optional[str] = None
    dataset_hash: Optional[str] = None
    artifact_hash: Optional[str] = None

class ContextSnapshotSchema(BaseModel):
    prompt_ref: PromptRefSchema
    dataset_ref: DatasetRefSchema
    telemetry_ref: TelemetryRefSchema
    artifact_ref: ArtifactRefSchema
    replay_metadata: ReplayMetadataSchema

class CreateJournalRequest(BaseModel):
    decision_id: str
    proposing_agent_id: str
    signature: str
    thesis_urn: str
    context_snapshot: ContextSnapshotSchema
    probability: float = 1.0

class CreateRevisionRequest(BaseModel):
    revision_id: str
    parent_decision_id: str
    proposing_agent_id: str
    signature: str
    correction_reason: str
    context_snapshot: ContextSnapshotSchema

class EvidenceSchema(BaseModel):
    evidence_id: str
    description: str
    artifact_ref: ArtifactRefSchema
    attached_at: datetime

class AttachEvidenceRequest(BaseModel):
    evidence_id: str
    decision_id: str
    attached_by_agent_id: str
    signature: str
    evidence: EvidenceSchema

class ReplayRequest(BaseModel):
    decision_id: str
    expected_hash: str
    context_uri: str

def map_snapshot(schema: ContextSnapshotSchema) -> DecisionContextSnapshot:
    return DecisionContextSnapshot(
        prompt_ref=PromptReference(schema.prompt_ref.prompt_id, schema.prompt_ref.prompt_hash, schema.prompt_ref.template_urn),
        dataset_ref=DatasetReference(schema.dataset_ref.dataset_id, schema.dataset_ref.dataset_hash, schema.dataset_ref.dataset_urn),
        telemetry_ref=TelemetryReference(schema.telemetry_ref.telemetry_id, schema.telemetry_ref.telemetry_hash, schema.telemetry_ref.span_id),
        artifact_ref=ArtifactReference(schema.artifact_ref.artifact_id, schema.artifact_ref.artifact_hash, schema.artifact_ref.artifact_urn),
        replay_metadata=ReplayMetadata(
            git_commit=schema.replay_metadata.git_commit,
            runtime_image=schema.replay_metadata.runtime_image,
            seed=schema.replay_metadata.seed,
            temperature=schema.replay_metadata.temperature,
            regime_identifier=schema.replay_metadata.regime_identifier,
            prompt_hash=schema.replay_metadata.prompt_hash,
            dataset_hash=schema.replay_metadata.dataset_hash,
            artifact_hash=schema.replay_metadata.artifact_hash
        )
    )

@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_journal(req: CreateJournalRequest, svc: DecisionJournalService = Depends(get_service)):
    try:
        snapshot = map_snapshot(req.context_snapshot)
        journal = svc.create_journal(
            decision_id=req.decision_id,
            proposing_agent_id=req.proposing_agent_id,
            signature=req.signature,
            thesis_urn=req.thesis_urn,
            context_snapshot=snapshot,
            probability=req.probability
        )
        return {
            "status": "CREATED",
            "decision_id": journal.decision_id,
            "thesis_urn": journal.thesis_urn,
            "created_at": journal.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DecisionJournalException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.post("/revision/create", status_code=status.HTTP_201_CREATED)
def create_revision(req: CreateRevisionRequest, svc: DecisionJournalService = Depends(get_service)):
    try:
        snapshot = map_snapshot(req.context_snapshot)
        revision = svc.create_revision(
            revision_id=req.revision_id,
            parent_decision_id=req.parent_decision_id,
            proposing_agent_id=req.proposing_agent_id,
            signature=req.signature,
            correction_reason=req.correction_reason,
            context_snapshot=snapshot
        )
        return {
            "status": "CREATED",
            "revision_id": revision.revision_id,
            "root_decision_id": revision.root_decision_id,
            "created_at": revision.created_at.isoformat()
        }
    except HindsightValidationException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except LineageIntegrityException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DecisionJournalException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.post("/evidence/attach", status_code=status.HTTP_200_OK)
def attach_evidence(req: AttachEvidenceRequest, svc: DecisionJournalService = Depends(get_service)):
    try:
        evidence_obj = DecisionEvidence(
            evidence_id=req.evidence.evidence_id,
            description=req.evidence.description,
            artifact_ref=ArtifactReference(
                req.evidence.artifact_ref.artifact_id,
                req.evidence.artifact_ref.artifact_hash,
                req.evidence.artifact_ref.artifact_urn
            ),
            attached_at=req.evidence.attached_at
        )
        agg = svc.attach_evidence(
            evidence_id=req.evidence_id,
            decision_id=req.decision_id,
            attached_by_agent_id=req.attached_by_agent_id,
            signature=req.signature,
            evidence=evidence_obj
        )
        return {
            "status": "ATTACHED",
            "evidence_id": agg.evidence_id,
            "decision_id": agg.decision_id
        }
    except LineageIntegrityException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/lineage/{root_decision_id}")
def get_lineage(root_decision_id: str, resolver: JournalLineageResolver = Depends(get_resolver)):
    try:
        projection = resolver.resolve_lineage(root_decision_id)
        return {
            "root_decision_id": projection.root_decision_id,
            "nodes": projection.nodes,
            "parent_map": projection.parent_map
        }
    except LineageIntegrityException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/active_leaf/{root_decision_id}")
def get_active_leaf(root_decision_id: str, resolver: JournalLineageResolver = Depends(get_resolver)):
    try:
        leaf_id = resolver.resolve_active_leaf(root_decision_id)
        return {"root_decision_id": root_decision_id, "active_leaf_decision_id": leaf_id}
    except DecisionJournalException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/replay")
def replay_decision(req: ReplayRequest, replay_svc: ReplayService = Depends(get_replay)):
    try:
        projection = replay_svc.replay_decision(
            decision_id=req.decision_id,
            expected_hash=req.expected_hash,
            context_uri=req.context_uri
        )
        return {
            "decision_id": projection.decision_id,
            "verified": projection.verified,
            "context_snapshot": {
                "replay_metadata": {
                    "git_commit": projection.context_snapshot.replay_metadata.git_commit,
                    "runtime_image": projection.context_snapshot.replay_metadata.runtime_image,
                    "seed": projection.context_snapshot.replay_metadata.seed,
                    "temperature": projection.context_snapshot.replay_metadata.temperature,
                    "regime_identifier": projection.context_snapshot.replay_metadata.regime_identifier,
                    "prompt_hash": projection.context_snapshot.replay_metadata.prompt_hash,
                    "dataset_hash": projection.context_snapshot.replay_metadata.dataset_hash,
                    "artifact_hash": projection.context_snapshot.replay_metadata.artifact_hash
                }
            }
        }
    except VerificationFailedException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
