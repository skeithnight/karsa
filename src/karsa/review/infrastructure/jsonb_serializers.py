"""JSONB serialization/deserialization for Review Engine — Sprint-07 Wave-2C.

Provides deterministic serialization for all domain value objects
stored as JSONB columns in PostgreSQL.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot, StructuredAssumption
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot, AssumptionValidation
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis
from karsa.review.domain.value_objects.review_verdict import ReviewType, ReviewVerdict


# --- DecisionSnapshot ---

def serialize_decision_snapshot(ds: DecisionSnapshot) -> Dict[str, Any]:
    return {
        "decision_id": ds.decision_id,
        "proposal_id": ds.proposal_id,
        "journal_ref": ds.journal_ref,
        "action_type": ds.action_type,
        "target_node_type": ds.target_node_type,
        "target_node_id": ds.target_node_id,
        "allocated_weights": ds.allocated_weights,
        "policy_snapshot": ds.policy_snapshot,
        "expected_return_bps": ds.expected_return_bps,
        "expected_drawdown_pct": ds.expected_drawdown_pct,
        "expected_sharpe_ratio": ds.expected_sharpe_ratio,
        "expected_horizon_days": ds.expected_horizon_days,
        "confidence_level": ds.confidence_level,
        "benchmark_urn": ds.benchmark_urn,
        "regime_at_decision": ds.regime_at_decision,
        "key_assumptions": [
            {"assumption_id": a.assumption_id, "statement": a.statement,
             "validation_criteria": a.validation_criteria, "source_urn": a.source_urn}
            for a in ds.key_assumptions
        ],
        "attribution_expectations": ds.attribution_expectations,
        "decision_rationale": ds.decision_rationale,
        "decision_confidence": ds.decision_confidence,
        "decision_timestamp": ds.decision_timestamp,
        "cryptographic_signature": ds.cryptographic_signature,
        "snapshot_hash": ds.snapshot_hash,
    }


def deserialize_decision_snapshot(data: Dict[str, Any]) -> DecisionSnapshot:
    assumptions = [
        StructuredAssumption(
            assumption_id=a["assumption_id"],
            statement=a["statement"],
            validation_criteria=a["validation_criteria"],
            source_urn=a.get("source_urn"),
        )
        for a in data.get("key_assumptions", [])
    ]
    return DecisionSnapshot(
        decision_id=data["decision_id"],
        proposal_id=data.get("proposal_id"),
        journal_ref=data["journal_ref"],
        action_type=data["action_type"],
        target_node_type=data["target_node_type"],
        target_node_id=data["target_node_id"],
        allocated_weights=data["allocated_weights"],
        policy_snapshot=data["policy_snapshot"],
        expected_return_bps=data["expected_return_bps"],
        expected_drawdown_pct=data["expected_drawdown_pct"],
        expected_sharpe_ratio=data["expected_sharpe_ratio"],
        expected_horizon_days=data["expected_horizon_days"],
        confidence_level=data["confidence_level"],
        benchmark_urn=data.get("benchmark_urn"),
        regime_at_decision=data.get("regime_at_decision"),
        key_assumptions=assumptions,
        attribution_expectations=data.get("attribution_expectations", {}),
        decision_rationale=data["decision_rationale"],
        decision_confidence=data["decision_confidence"],
        decision_timestamp=data["decision_timestamp"],
        cryptographic_signature=data["cryptographic_signature"],
        snapshot_hash=data["snapshot_hash"],
    )


# --- SchedulePolicy ---

def serialize_schedule_policy(sp: SchedulePolicy) -> Dict[str, Any]:
    return {
        "observation_window_days": sp.observation_window_days,
        "overdue_threshold_days": sp.overdue_threshold_days,
        "review_due_date": sp.review_due_date,
        "auto_expire": sp.auto_expire,
    }


def deserialize_schedule_policy(data: Dict[str, Any]) -> SchedulePolicy:
    return SchedulePolicy(
        observation_window_days=data["observation_window_days"],
        overdue_threshold_days=data["overdue_threshold_days"],
        review_due_date=data["review_due_date"],
        auto_expire=data.get("auto_expire", False),
    )


# --- ReviewTemplate ---

def serialize_review_template(rt: ReviewTemplate) -> Dict[str, Any]:
    return {
        "template_id": rt.template_id,
        "review_type": rt.review_type.value,
        "required_metrics": rt.required_metrics,
        "required_assumptions": rt.required_assumptions,
        "evaluation_criteria": rt.evaluation_criteria,
        "scoring_rules": rt.scoring_rules,
        "extensible_config": rt.extensible_config,
    }


def deserialize_review_template(data: Dict[str, Any]) -> ReviewTemplate:
    return ReviewTemplate(
        template_id=data["template_id"],
        review_type=ReviewType(data["review_type"]),
        required_metrics=data["required_metrics"],
        required_assumptions=data["required_assumptions"],
        evaluation_criteria=data["evaluation_criteria"],
        scoring_rules=data["scoring_rules"],
        extensible_config=data.get("extensible_config", {}),
    )


# --- ActualOutcomeSnapshot ---

def serialize_actual_outcome(ao: ActualOutcomeSnapshot) -> Dict[str, Any]:
    return {
        "evaluation_id": ao.evaluation_id,
        "target_urn": ao.target_urn,
        "observation_window_days": ao.observation_window_days,
        "realized_return_bps": ao.realized_return_bps,
        "realized_drawdown_pct": ao.realized_drawdown_pct,
        "realized_sharpe_ratio": ao.realized_sharpe_ratio,
        "benchmark_return_bps": ao.benchmark_return_bps,
        "regime_during_period": ao.regime_during_period,
        "assumption_validations": [
            {"assumption_id": v.assumption_id, "statement": v.statement,
             "expected": v.expected, "actual": v.actual,
             "validated": v.validated, "impact_bps": v.impact_bps}
            for v in ao.assumption_validations
        ],
        "actual_attribution": ao.actual_attribution,
        "generated_at": ao.generated_at,
    }


def deserialize_actual_outcome(data: Dict[str, Any]) -> ActualOutcomeSnapshot:
    validations = [
        AssumptionValidation(
            assumption_id=v["assumption_id"],
            statement=v["statement"],
            expected=v["expected"],
            actual=v["actual"],
            validated=v["validated"],
            impact_bps=v.get("impact_bps", 0.0),
        )
        for v in data.get("assumption_validations", [])
    ]
    return ActualOutcomeSnapshot(
        evaluation_id=data["evaluation_id"],
        target_urn=data["target_urn"],
        observation_window_days=data["observation_window_days"],
        realized_return_bps=data["realized_return_bps"],
        realized_drawdown_pct=data["realized_drawdown_pct"],
        realized_sharpe_ratio=data["realized_sharpe_ratio"],
        benchmark_return_bps=data["benchmark_return_bps"],
        regime_during_period=data.get("regime_during_period"),
        assumption_validations=validations,
        actual_attribution=data.get("actual_attribution", {}),
        generated_at=data.get("generated_at"),
    )


# --- VarianceAnalysis ---

def serialize_variance(va: VarianceAnalysis) -> Dict[str, Any]:
    return {
        "return_variance_bps": va.return_variance_bps,
        "drawdown_variance_pct": va.drawdown_variance_pct,
        "sharpe_variance": va.sharpe_variance,
        "confidence_accuracy": va.confidence_accuracy,
        "assumption_accuracy": va.assumption_accuracy,
        "overall_accuracy": va.overall_accuracy,
    }


def deserialize_variance(data: Dict[str, Any]) -> VarianceAnalysis:
    return VarianceAnalysis(
        return_variance_bps=data["return_variance_bps"],
        drawdown_variance_pct=data["drawdown_variance_pct"],
        sharpe_variance=data["sharpe_variance"],
        confidence_accuracy=data["confidence_accuracy"],
        assumption_accuracy=data["assumption_accuracy"],
        overall_accuracy=data["overall_accuracy"],
    )


# --- Generic JSONB helpers ---

def to_jsonb(data: Any) -> str:
    """Serializes data to JSON string for JSONB storage."""
    return json.dumps(data, default=str, sort_keys=True)


def from_jsonb(data: Any) -> Any:
    """Deserializes JSONB data from PostgreSQL."""
    if isinstance(data, str):
        return json.loads(data)
    return data  # Already a dict/list from psycopg JSONB adapter
