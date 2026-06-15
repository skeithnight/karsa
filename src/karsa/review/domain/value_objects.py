import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class DecisionQualityAssessment:
    outcome_independent_score: float
    outcome_dependent_score: float
    hindsight_bias_deviation: float

    def __post_init__(self):
        # Validation rules
        if not (0.0 <= self.outcome_independent_score <= 1.0):
            raise ValueError(f"outcome_independent_score must be between 0.0 and 1.0, got {self.outcome_independent_score}")
        if not (0.0 <= self.outcome_dependent_score <= 1.0):
            raise ValueError(f"outcome_dependent_score must be between 0.0 and 1.0, got {self.outcome_dependent_score}")
        
        # Deviation validation with float tolerance (1e-6)
        expected_dev = self.outcome_dependent_score - self.outcome_independent_score
        if abs(self.hindsight_bias_deviation - expected_dev) > 1e-6:
            raise ValueError(
                f"hindsight_bias_deviation ({self.hindsight_bias_deviation}) "
                f"must equal outcome_dependent_score - outcome_independent_score ({expected_dev})"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_independent_score": self.outcome_independent_score,
            "outcome_dependent_score": self.outcome_dependent_score,
            "hindsight_bias_deviation": self.hindsight_bias_deviation
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionQualityAssessment':
        return cls(
            outcome_independent_score=float(data["outcome_independent_score"]),
            outcome_dependent_score=float(data["outcome_dependent_score"]),
            hindsight_bias_deviation=float(data["hindsight_bias_deviation"])
        )


@dataclass(frozen=True)
class FailureClassification:
    thesis_error: bool
    execution_error: bool
    timing_error: bool
    sizing_error: bool
    calibration_error: bool

    def __post_init__(self):
        if not all(isinstance(val, bool) for val in (self.thesis_error, self.execution_error, self.timing_error, self.sizing_error, self.calibration_error)):
            raise ValueError("All FailureClassification flags must be booleans")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thesis_error": self.thesis_error,
            "execution_error": self.execution_error,
            "timing_error": self.timing_error,
            "sizing_error": self.sizing_error,
            "calibration_error": self.calibration_error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailureClassification':
        return cls(
            thesis_error=bool(data["thesis_error"]),
            execution_error=bool(data["execution_error"]),
            timing_error=bool(data["timing_error"]),
            sizing_error=bool(data["sizing_error"]),
            calibration_error=bool(data["calibration_error"])
        )


@dataclass(frozen=True)
class SuccessClassification:
    alpha_generation: bool
    execution_efficiency: bool
    risk_mitigation: bool

    def __post_init__(self):
        if not all(isinstance(val, bool) for val in (self.alpha_generation, self.execution_efficiency, self.risk_mitigation)):
            raise ValueError("All SuccessClassification flags must be booleans")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha_generation": self.alpha_generation,
            "execution_efficiency": self.execution_efficiency,
            "risk_mitigation": self.risk_mitigation
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuccessClassification':
        return cls(
            alpha_generation=bool(data["alpha_generation"]),
            execution_efficiency=bool(data["execution_efficiency"]),
            risk_mitigation=bool(data["risk_mitigation"])
        )


@dataclass(frozen=True)
class ImprovementRecommendation:
    recommendation_code: str
    recommendation_category: str
    recommendation_severity: str
    thesis_refinement_actions: List[str] = field(default_factory=list)

    ALLOWED_CODES = {
        "EXECUTION_WARNING",
        "THESIS_REVIEW_REQUIRED",
        "THESIS_SUSPEND_RECOMMENDED",
        "RISK_CONTROL_WARNING",
        "PROCESS_IMPROVEMENT_REQUIRED"
    }

    ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def __post_init__(self):
        if self.recommendation_code not in self.ALLOWED_CODES:
            raise ValueError(f"Invalid recommendation_code: {self.recommendation_code}")
        if self.recommendation_severity not in self.ALLOWED_SEVERITIES:
            raise ValueError(f"Invalid recommendation_severity: {self.recommendation_severity}")
        if not isinstance(self.recommendation_category, str) or not self.recommendation_category:
            raise ValueError("recommendation_category must be a non-empty string")
        if not isinstance(self.thesis_refinement_actions, list) or not all(isinstance(a, str) for a in self.thesis_refinement_actions):
            raise ValueError("thesis_refinement_actions must be a list of strings")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_code": self.recommendation_code,
            "recommendation_category": self.recommendation_category,
            "recommendation_severity": self.recommendation_severity,
            "thesis_refinement_actions": list(self.thesis_refinement_actions)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImprovementRecommendation':
        return cls(
            recommendation_code=data["recommendation_code"],
            recommendation_category=data["recommendation_category"],
            recommendation_severity=data["recommendation_severity"],
            thesis_refinement_actions=list(data.get("thesis_refinement_actions", []))
        )


@dataclass(frozen=True)
class ReviewMethodologyManifest:
    review_methodology_urn: str
    review_policy_hash: str
    review_prompt_version: str
    reviewer_model_version: str

    def __post_init__(self):
        if not self.review_methodology_urn or not isinstance(self.review_methodology_urn, str):
            raise ValueError("review_methodology_urn must be a non-empty string")
        if not self.review_policy_hash or not isinstance(self.review_policy_hash, str):
            raise ValueError("review_policy_hash must be a non-empty string")
        if not self.review_prompt_version or not isinstance(self.review_prompt_version, str):
            raise ValueError("review_prompt_version must be a non-empty string")
        if not self.reviewer_model_version or not isinstance(self.reviewer_model_version, str):
            raise ValueError("reviewer_model_version must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_methodology_urn": self.review_methodology_urn,
            "review_policy_hash": self.review_policy_hash,
            "review_prompt_version": self.review_prompt_version,
            "reviewer_model_version": self.reviewer_model_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewMethodologyManifest':
        return cls(
            review_methodology_urn=data["review_methodology_urn"],
            review_policy_hash=data["review_policy_hash"],
            review_prompt_version=data["review_prompt_version"],
            reviewer_model_version=data["reviewer_model_version"]
        )

    def compute_hash(self) -> str:
        # Canonical serialization: sort keys alphabetically, compact separators (no whitespace)
        payload = self.to_dict()
        canonical_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
