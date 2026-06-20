"""RebuildProjectionService — Sprint-07 Wave-3.

Rebuilds projections from source data.
Transaction boundary: Projection truncate + rebuild.
"""
from datetime import datetime

from karsa.review.domain.repositories.capability_score_projection_repository import CapabilityScoreProjectionRepository
from karsa.review.domain.repositories.review_coverage_projection_repository import ReviewCoverageProjectionRepository
from karsa.review.domain.repositories.review_cycle_status_projection_repository import ReviewCycleStatusProjectionRepository
from karsa.review.application.dto import RebuildProjectionCommand, RebuildProjectionResponse


class RebuildProjectionService:
    """Rebuilds projections from source data.

    Transaction boundary:
    1. Truncate projection table
    2. Recompute from source data
    """

    def __init__(
        self,
        capability_repo: CapabilityScoreProjectionRepository,
        coverage_repo: ReviewCoverageProjectionRepository,
        status_repo: ReviewCycleStatusProjectionRepository,
    ):
        self.capability_repo = capability_repo
        self.coverage_repo = coverage_repo
        self.status_repo = status_repo

    def execute(self, command: RebuildProjectionCommand) -> RebuildProjectionResponse:
        """Executes the rebuild projection command.

        All writes occur within a single transaction managed by the caller.

        Args:
            command: The rebuild projection command.

        Returns:
            RebuildProjectionResponse with rebuild details.

        Raises:
            ValueError: If projection name is invalid.
        """
        now = datetime.utcnow()

        if command.projection_name == "capability_score":
            self.capability_repo.rebuild()
            projections = self.capability_repo.list_all()
            return RebuildProjectionResponse(
                projection_name="capability_score",
                rows_affected=len(projections),
                rebuilt_at=now.isoformat(),
            )

        elif command.projection_name == "review_coverage":
            self.coverage_repo.rebuild()
            return RebuildProjectionResponse(
                projection_name="review_coverage",
                rows_affected=0,  # Coverage rebuild requires event replay
                rebuilt_at=now.isoformat(),
            )

        elif command.projection_name == "cycle_status":
            self.status_repo.rebuild()
            return RebuildProjectionResponse(
                projection_name="cycle_status",
                rows_affected=0,  # Status rebuild requires event replay
                rebuilt_at=now.isoformat(),
            )

        else:
            raise ValueError(f"Unknown projection: {command.projection_name}")
