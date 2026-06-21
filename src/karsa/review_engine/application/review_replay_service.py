"""ReviewReplayService — Sprint-10.

Deterministic replay from persisted state only.
Never queries upstream engines (Performance, Attribution).
"""
from typing import List, Optional, Dict, Any

from karsa.review_engine.domain.aggregates.review_assessment import ReviewAssessment
from karsa.review_engine.infrastructure.repositories.review_assessment_repository import ReviewAssessmentRepository
from karsa.review_engine.infrastructure.repositories.review_version_registry_repository import ReviewVersionRegistryRepository
from karsa.review_engine.infrastructure.repositories.review_projection_repository import ReviewProjectionRepository


class ReviewReplayService:
    """Deterministic replay from immutable persisted state.

    Rules:
    - Only reads from review_assessments and review_version_registry
    - Never queries Performance Engine
    - Never queries Attribution Engine
    - Rebuilds are deterministic
    """

    def __init__(
        self,
        assessment_repo: ReviewAssessmentRepository,
        registry_repo: ReviewVersionRegistryRepository,
        projection_repo: ReviewProjectionRepository,
    ):
        self.assessment_repo = assessment_repo
        self.registry_repo = registry_repo
        self.projection_repo = projection_repo

    def get_canonical_review(
        self, evaluation_id: str, review_type: str
    ) -> Optional[ReviewAssessment]:
        """Get canonical review by evaluation and type.

        Uses registry to find canonical, then loads assessment.
        Never queries upstream engines.
        """
        canonical = self.registry_repo.get_canonical(evaluation_id, review_type)
        if not canonical:
            return None
        return self.assessment_repo.get_by_id(canonical.review_id)

    def get_review_history(self, evaluation_id: str) -> List[Dict[str, Any]]:
        """Get all review versions for an evaluation.

        Returns version history from registry.
        """
        entries = self.registry_repo.list_by_evaluation(evaluation_id)
        return [
            {
                "version_id": e.version_id,
                "evaluation_id": e.evaluation_id,
                "review_type": e.review_type,
                "review_version": e.review_version,
                "review_id": e.review_id,
                "review_status": e.review_status,
                "superseded_by": e.superseded_by,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]

    def rebuild_projections(self) -> Dict[str, int]:
        """Rebuild all projections from immutable sources.

        Reads only from review_assessments JOIN review_version_registry.
        Never queries upstream engines.
        """
        # This delegates to the projection repository
        # Actual rebuild SQL is in Wave-6
        self.projection_repo.rebuild_all()
        return {"status": "rebuild_initiated"}
