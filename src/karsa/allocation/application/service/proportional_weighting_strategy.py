from typing import List, Dict, Any

from karsa.allocation.application.service.weighting_strategy import WeightingStrategy
from karsa.allocation.domain.model.value_objects import ProposedWeight, RiskBudget


class ProportionalWeightingStrategy(WeightingStrategy):
    """Sprint-06 implementation: proportional to ranking score.

    weight_i = score_i / sum(scores)

    Applies DiversificationCap (max_weight_per_worker) and
    ExplorationFloor (min_exploration_pct).
    """

    def compute_weights(
        self,
        ranked_workers: List[Dict[str, Any]],
        total_capital: float,
        max_weight_per_worker: float = 0.40,
        min_exploration_pct: float = 0.05,
    ) -> Dict[str, ProposedWeight]:
        # Filter to allocatable workers only
        allocatable = [
            w for w in ranked_workers
            if w.get("eligibility_status") == "ALLOCATABLE"
        ]

        if not allocatable:
            return {}

        # Extract scores
        scores = {}
        for w in allocatable:
            urn = w["worker_urn"]
            explanation = w.get("ranking_explanation", {})
            score = explanation.get("final_score", 0.0)
            scores[urn] = max(score, 0.0)

        total_score = sum(scores.values())
        if total_score <= 0:
            # Equal weight if all scores are zero
            equal_weight = (1.0 - min_exploration_pct) / len(allocatable)
            return self._build_weights(allocatable, {urn: equal_weight for urn in scores}, total_capital)

        # Proportional weights
        raw_weights = {urn: score / total_score for urn, score in scores.items()}

        # Apply diversification cap
        capped_weights = {}
        excess = 0.0
        uncapped_count = 0
        for urn, weight in raw_weights.items():
            if weight > max_weight_per_worker:
                capped_weights[urn] = max_weight_per_worker
                excess += weight - max_weight_per_worker
            else:
                capped_weights[urn] = weight
                uncapped_count += 1

        # Redistribute excess to uncapped workers
        if excess > 0 and uncapped_count > 0:
            redistribution = excess / uncapped_count
            for urn in capped_weights:
                if raw_weights[urn] <= max_weight_per_worker:
                    capped_weights[urn] = min(
                        capped_weights[urn] + redistribution,
                        max_weight_per_worker
                    )

        # Normalize to ensure sum <= 1.0
        total_weight = sum(capped_weights.values())
        if total_weight > 1.0:
            scale = 1.0 / total_weight
            capped_weights = {urn: w * scale for urn, w in capped_weights.items()}

        return self._build_weights(allocatable, capped_weights, total_capital)

    def _build_weights(
        self,
        allocatable: List[Dict[str, Any]],
        weights: Dict[str, float],
        total_capital: float,
    ) -> Dict[str, ProposedWeight]:
        worker_map = {w["worker_urn"]: w for w in allocatable}
        result = {}

        for urn, weight in weights.items():
            w = worker_map[urn]
            explanation = w.get("ranking_explanation", {})
            score = explanation.get("final_score", 0.0)
            max_dd = w.get("max_drawdown", 0.0)

            rationale = (
                f"Proportional allocation based on ranking score {score:.4f}. "
                f"Cumulative alpha: {w.get('cumulative_alpha', 0.0):.4f}, "
                f"Max drawdown: {max_dd:.4f}, "
                f"Observations: {w.get('observation_count', 0)}."
            )

            result[urn] = ProposedWeight(
                worker_urn=urn,
                proposed_weight=round(weight, 6),
                ranking_score=score,
                eligibility_status=w.get("eligibility_status", "ALLOCATABLE"),
                rationale=rationale,
                risk_budget=RiskBudget(
                    max_volatility=0.15,
                    max_drawdown=max(max_dd * 2.0, 0.10),
                    max_exposure=0.40,
                ),
            )

        return result
