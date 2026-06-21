"""ReviewVersioningService — Sprint-10.

Canonical version governance via review_version_registry.
Uses repository layer only. No direct SQL.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from karsa.review_engine.infrastructure.repositories.review_version_registry_repository import (
    ReviewVersionRegistryRepository, VersionRegistryEntry,
)
from karsa.review_engine.infrastructure.repositories.review_assessment_repository import ReviewAssessmentRepository
from karsa.review_engine.domain.events.review_events import ReviewCanonicalVersionChangedEvent


class ReviewVersioningService:
    """Version governance for review assessments. ADR-107."""

    def __init__(
        self,
        registry_repo: ReviewVersionRegistryRepository,
        assessment_repo: ReviewAssessmentRepository,
    ):
        self.registry_repo = registry_repo
        self.assessment_repo = assessment_repo

    def get_canonical(self, evaluation_id: str, review_type: str) -> Optional[VersionRegistryEntry]:
        """Get canonical review for evaluation and type."""
        return self.registry_repo.get_canonical(evaluation_id, review_type)

    def register_canonical(
        self,
        evaluation_id: str,
        review_type: str,
        review_version: str,
        review_id: str,
    ) -> VersionRegistryEntry:
        """Register a new canonical review. Supersedes previous if exists."""
        now = datetime.utcnow()

        # Supersede previous canonical
        self.registry_repo.supersede_previous(evaluation_id, review_type, review_id)

        # Create new canonical entry
        entry = VersionRegistryEntry(
            version_id=str(uuid.uuid4()),
            evaluation_id=evaluation_id,
            review_type=review_type,
            review_version=review_version,
            review_id=review_id,
            review_status="CANONICAL",
            superseded_by=None,
            created_at=now,
            updated_at=now,
        )
        self.registry_repo.save(entry)
        return entry

    def promote_experimental(
        self,
        evaluation_id: str,
        review_type: str,
        review_version: str,
    ) -> Optional[VersionRegistryEntry]:
        """Promote experimental review to canonical."""
        entry = self.registry_repo.get_by_evaluation_and_version(
            evaluation_id, review_type, review_version
        )
        if not entry or entry.review_status != "EXPERIMENTAL":
            return None

        # Supersede current canonical
        self.registry_repo.supersede_previous(evaluation_id, review_type, entry.review_id)

        # Update entry to canonical
        now = datetime.utcnow()
        promoted = VersionRegistryEntry(
            version_id=entry.version_id,
            evaluation_id=evaluation_id,
            review_type=review_type,
            review_version=review_version,
            review_id=entry.review_id,
            review_status="CANONICAL",
            superseded_by=None,
            created_at=entry.created_at,
            updated_at=now,
        )
        self.registry_repo.save(promoted)
        return promoted

    def list_history(self, evaluation_id: str) -> List[VersionRegistryEntry]:
        """List all version entries for an evaluation."""
        return self.registry_repo.list_by_evaluation(evaluation_id)

    def create_version_changed_event(
        self,
        evaluation_id: str,
        review_type: str,
        previous_review_id: Optional[str],
        new_review_id: str,
        changed_by: str,
    ) -> ReviewCanonicalVersionChangedEvent:
        """Create version changed event."""
        return ReviewCanonicalVersionChangedEvent(
            event_id=str(uuid.uuid4()),
            evaluation_id=evaluation_id,
            review_type=review_type,
            previous_review_id=previous_review_id,
            new_review_id=new_review_id,
            changed_at=datetime.utcnow().isoformat(),
            changed_by=changed_by,
        )
