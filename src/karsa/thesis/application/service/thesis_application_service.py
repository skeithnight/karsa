from typing import Optional
from datetime import datetime, timezone

from karsa.thesis.domain.model.thesis import ActiveThesis, ThesisReview
from karsa.thesis.domain.repository.thesis_repository import ThesisRepository
from karsa.thesis.application.port.memory_platform_port import MemoryPlatformPort, ArtifactPayload

class ThesisApplicationService:
    def __init__(self, repository: ThesisRepository, memory_port: MemoryPlatformPort):
        self.repository = repository
        self.memory_port = memory_port

    def create_thesis(self, thesis_id: str, author: str) -> None:
        thesis = ActiveThesis(thesis_id=thesis_id, author=author, created_at=datetime.now(timezone.utc))
        self.repository.save(thesis)
        
        self.memory_port.publish_artifact(
            ArtifactPayload(
                thesis_id=thesis.thesis_id,
                state=thesis.state.value,
                author=thesis.author,
                event_type="THESIS_CREATED",
                details={}
            )
        )

    def degrade_thesis(self, thesis_id: str) -> None:
        thesis = self.repository.get_by_id(thesis_id)
        if not thesis:
            raise ValueError(f"Thesis {thesis_id} not found")
            
        thesis.degrade()
        self.repository.save(thesis)
        
        self.memory_port.publish_artifact(
            ArtifactPayload(
                thesis_id=thesis.thesis_id,
                state=thesis.state.value,
                author=thesis.author,
                event_type="THESIS_DEGRADED",
                details={}
            )
        )

    def request_review(self, thesis_id: str) -> None:
        thesis = self.repository.get_by_id(thesis_id)
        if not thesis:
            raise ValueError(f"Thesis {thesis_id} not found")
            
        thesis.request_review()
        self.repository.save(thesis)
        
        self.memory_port.publish_artifact(
            ArtifactPayload(
                thesis_id=thesis.thesis_id,
                state=thesis.state.value,
                author=thesis.author,
                event_type="REVIEW_REQUESTED",
                details={}
            )
        )

    def confirm_thesis(self, thesis_id: str, review_id: str, reviewer: str, outcome: str, notes: str) -> None:
        thesis = self.repository.get_by_id(thesis_id)
        if not thesis:
            raise ValueError(f"Thesis {thesis_id} not found")
            
        review = ThesisReview(
            review_id=review_id,
            reviewer=reviewer,
            reviewed_at=datetime.now(timezone.utc),
            outcome=outcome,
            notes=notes
        )
        
        thesis.confirm(review)
        self.repository.save(thesis)
        
        self.memory_port.publish_artifact(
            ArtifactPayload(
                thesis_id=thesis.thesis_id,
                state=thesis.state.value,
                author=thesis.author,
                event_type="THESIS_CONFIRMED",
                details={"review_id": review_id, "reviewer": reviewer, "outcome": outcome}
            )
        )

    def invalidate_thesis(self, thesis_id: str, reason: str) -> None:
        thesis = self.repository.get_by_id(thesis_id)
        if not thesis:
            raise ValueError(f"Thesis {thesis_id} not found")
            
        thesis.invalidate(reason)
        self.repository.save(thesis)
        
        self.memory_port.publish_artifact(
            ArtifactPayload(
                thesis_id=thesis.thesis_id,
                state=thesis.state.value,
                author=thesis.author,
                event_type="THESIS_INVALIDATED",
                details={"reason": reason}
            )
        )

    def retire_thesis(self, thesis_id: str, reason: str) -> None:
        thesis = self.repository.get_by_id(thesis_id)
        if not thesis:
            raise ValueError(f"Thesis {thesis_id} not found")
            
        thesis.retire(reason)
        self.repository.save(thesis)
        
        self.memory_port.publish_artifact(
            ArtifactPayload(
                thesis_id=thesis.thesis_id,
                state=thesis.state.value,
                author=thesis.author,
                event_type="THESIS_RETIRED",
                details={"reason": reason}
            )
        )
