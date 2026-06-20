from abc import ABC, abstractmethod
from typing import List, Dict, Any

from karsa.allocation.domain.model.value_objects import ProposedWeight


class WeightingStrategy(ABC):
    """Port for computing allocation weights from ranked workers."""

    @abstractmethod
    def compute_weights(
        self,
        ranked_workers: List[Dict[str, Any]],
        total_capital: float,
        max_weight_per_worker: float = 0.40,
        min_exploration_pct: float = 0.05,
    ) -> Dict[str, ProposedWeight]:
        """Computes proposed weights for allocatable workers.

        Args:
            ranked_workers: List of worker dicts from allocation readiness API.
            total_capital: Total capital to allocate.
            max_weight_per_worker: Maximum weight any single worker can receive.
            min_exploration_pct: Minimum weight reserved for exploration.

        Returns:
            Dict mapping worker_urn to ProposedWeight.
        """
        pass
