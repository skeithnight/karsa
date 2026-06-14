import math
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
class DecisionRationale:
    reasoning_steps: str
    market_assumptions: str

    def __post_init__(self):
        if not self.reasoning_steps or not self.reasoning_steps.strip():
            raise ValueError("reasoning_steps cannot be empty.")
        if not self.market_assumptions or not self.market_assumptions.strip():
            raise ValueError("market_assumptions cannot be empty.")

@dataclass(frozen=True)
class DecisionHypothesis:
    thesis_urn: str
    expected_return_bps: int
    validity_horizon_seconds: int

    def __post_init__(self):
        if not self.thesis_urn or not self.thesis_urn.strip():
            raise ValueError("thesis_urn cannot be empty.")
        if self.expected_return_bps <= 0:
            raise ValueError("expected_return_bps must be greater than 0.")
        if self.validity_horizon_seconds <= 0:
            raise ValueError("validity_horizon_seconds must be greater than 0.")

@dataclass(frozen=True)
class DecisionConfidence:
    probability: float
    standard_deviation: float

    def __post_init__(self):
        # Enforce NaN/Inf checks
        if math.isnan(self.probability) or math.isinf(self.probability):
            raise ValueError("probability cannot be NaN or infinite.")
        if math.isnan(self.standard_deviation) or math.isinf(self.standard_deviation):
            raise ValueError("standard_deviation cannot be NaN or infinite.")
            
        # Enforce boundary checks
        if not (0.0 <= self.probability <= 1.0):
            raise ValueError(f"probability {self.probability} must be between 0.0 and 1.0.")
        if self.standard_deviation < 0.0:
            raise ValueError("standard_deviation cannot be negative.")

@dataclass(frozen=True)
class DecisionContextSnapshot:
    prompt_ref: PromptReference
    dataset_ref: DatasetReference
    telemetry_ref: TelemetryReference
    artifact_ref: ArtifactReference
    replay_metadata: ReplayMetadata
    rationale: DecisionRationale = DecisionRationale("Default Reasoning", "Default Assumptions")
    hypothesis: DecisionHypothesis = DecisionHypothesis("urn:thesis:default", 100, 3600)
    confidence: DecisionConfidence = DecisionConfidence(1.0, 0.0)

@dataclass(frozen=True)
class DecisionEvidence:
    evidence_id: str
    description: str
    artifact_ref: ArtifactReference
    attached_at: datetime
