"""ReviewProjectionRepository — Sprint-10.

Read-only repository for review projections.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ReviewProjectionRepository(ABC):
    """Read-only repository for review projections.

    Projections are rebuilt from review_assessments JOIN review_version_registry.
    Actual rebuild logic belongs to Wave-6.
    """

    @abstractmethod
    def get_worker_review(self, target_urn: str) -> Optional[Dict[str, Any]]:
        """Get worker review projection."""
        ...

    @abstractmethod
    def get_thesis_review(self, thesis_urn: str) -> Optional[Dict[str, Any]]:
        """Get thesis review projection."""
        ...

    @abstractmethod
    def get_capability_gaps(self, target_urn: str) -> List[Dict[str, Any]]:
        """Get capability gap projections for a target."""
        ...

    @abstractmethod
    def rebuild_all(self) -> None:
        """Rebuild all projections. Wave-6 implementation."""
        raise NotImplementedError("rebuild_all belongs to Wave-6")
