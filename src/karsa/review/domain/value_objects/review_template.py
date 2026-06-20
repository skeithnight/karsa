"""ReviewTemplate value object — Sprint-07 Wave-1."""
from dataclasses import dataclass, field
from typing import List, Dict, Any

from karsa.review.domain.value_objects.review_verdict import ReviewType


@dataclass(frozen=True)
class ReviewTemplate:
    """Defines evaluation criteria for a review type.

    Different review types require different metrics, assumptions,
    and scoring rules.
    """
    template_id: str
    review_type: ReviewType
    required_metrics: List[str]
    required_assumptions: List[str]
    evaluation_criteria: Dict[str, Any]
    scoring_rules: Dict[str, float]
    extensible_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.template_id or not self.template_id.strip():
            raise ValueError("template_id cannot be empty.")
        if not self.required_metrics:
            raise ValueError("required_metrics cannot be empty.")

    @classmethod
    def default_allocation_review(cls) -> "ReviewTemplate":
        """Default template for allocation reviews."""
        return cls(
            template_id="tmpl-allocation-default",
            review_type=ReviewType.ALLOCATION_REVIEW,
            required_metrics=["return_bps", "drawdown_pct", "sharpe_ratio"],
            required_assumptions=["market_regime", "worker_capability"],
            evaluation_criteria={
                "return_threshold_bps": 0,
                "drawdown_threshold_pct": 10.0,
                "sharpe_threshold": 0.5,
            },
            scoring_rules={
                "outperform_threshold": 1.2,
                "underperform_threshold": 0.8,
                "fail_threshold": 0.5,
            },
        )
