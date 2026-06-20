import hashlib
import json
from typing import Dict, Any, List

from karsa.allocation.domain.model.value_objects import ProposedWeight


class ContextHashService:
    """Generates deterministic SHA-256 hashes for proposal context snapshots."""

    def generate_context_hash(
        self,
        workers: List[Dict[str, Any]],
        policy_id: str,
        weights: Dict[str, ProposedWeight],
    ) -> str:
        """Generates a deterministic SHA-256 hash of the proposal context.

        Args:
            workers: Ranked worker data from allocation readiness.
            policy_id: Active policy identifier.
            weights: Computed proposed weights.

        Returns:
            Hex-encoded SHA-256 hash string.
        """
        context_data = {
            "policy_id": policy_id,
            "workers": sorted(
                [
                    {
                        "worker_urn": w.get("worker_urn", ""),
                        "eligibility_status": w.get("eligibility_status", ""),
                        "cumulative_alpha": w.get("cumulative_alpha", 0.0),
                        "max_drawdown": w.get("max_drawdown", 0.0),
                        "observation_count": w.get("observation_count", 0),
                    }
                    for w in workers
                ],
                key=lambda x: x["worker_urn"],
            ),
            "weights": {
                urn: round(pw.proposed_weight, 10)
                for urn, pw in sorted(weights.items())
            },
        }
        serialized = json.dumps(context_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
