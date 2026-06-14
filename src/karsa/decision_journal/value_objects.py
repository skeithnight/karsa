from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class PromptReference:
    prompt_id: str
    prompt_hash: str
    template_urn: str

@dataclass(frozen=True)
class DatasetReference:
    dataset_id: str
    dataset_hash: str
    dataset_urn: str

@dataclass(frozen=True)
class TelemetryReference:
    telemetry_id: str
    telemetry_hash: str
    span_id: str

@dataclass(frozen=True)
class ArtifactReference:
    artifact_id: str
    artifact_hash: str
    artifact_urn: str

@dataclass(frozen=True)
class ReplayMetadata:
    git_commit: str
    runtime_image: str
    seed: Optional[int]
    temperature: Optional[float]
    regime_identifier: Optional[str]
    prompt_hash: Optional[str] = None
    dataset_hash: Optional[str] = None
    artifact_hash: Optional[str] = None

@dataclass(frozen=True)
class DecisionContextSnapshot:
    prompt_ref: PromptReference
    dataset_ref: DatasetReference
    telemetry_ref: TelemetryReference
    artifact_ref: ArtifactReference
    replay_metadata: ReplayMetadata

@dataclass(frozen=True)
class DecisionEvidence:
    evidence_id: str
    description: str
    artifact_ref: ArtifactReference
    attached_at: datetime
