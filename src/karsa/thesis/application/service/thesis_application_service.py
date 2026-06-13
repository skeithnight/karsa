import json
from dataclasses import asdict
from karsa.shared.infrastructure.uow import UnitOfWork
from karsa.shared.infrastructure.outbox import OutboxRecord
from karsa.thesis.application.commands import (
    ProposeThesisCommand, AddContributorCommand, UpdateConfidenceCommand,
    InvalidateThesisCommand, GovernanceDecisionPayload, RecordReviewCommand
)
from karsa.thesis.domain.model.thesis import Thesis
from karsa.thesis.infrastructure.storage.thesis_repository import ThesisRepository
from karsa.thesis.events.factory import ThesisEventFactory

class ThesisApplicationService:
    def __init__(self, uow: UnitOfWork, repo: ThesisRepository):
        self.uow = uow
        self.repo = repo

    def propose_thesis(self, cmd: ProposeThesisCommand) -> str:
        with self.uow:
            thesis = Thesis(
                thesis_id=cmd.thesis_id,
                originator=cmd.originator,
                hypothesis=cmd.hypothesis,
                confidence=cmd.confidence,
                time_horizon=cmd.time_horizon,
                research_lineage=cmd.research_lineage
            )
            thesis.propose()
            self.repo.save(thesis)
            
            event = ThesisEventFactory.build_proposed(thesis)
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)), 
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)
            
        return cmd.thesis_id

    def add_contributor(self, cmd: AddContributorCommand) -> None:
        with self.uow:
            thesis = self.repo.get_by_id(cmd.thesis_id)
            if not thesis:
                raise ValueError("Thesis not found")
            
            thesis.add_contributor(cmd.contributor)
            self.repo.save(thesis)

    def update_confidence(self, cmd: UpdateConfidenceCommand) -> None:
        with self.uow:
            thesis = self.repo.get_by_id(cmd.thesis_id)
            if not thesis:
                raise ValueError("Thesis not found")
            
            thesis.update_confidence(cmd.confidence)
            self.repo.save(thesis)
            
            event = ThesisEventFactory.build_confidence_updated(thesis)
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)),
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)

    def invalidate_thesis(self, cmd: InvalidateThesisCommand) -> None:
        with self.uow:
            thesis = self.repo.get_by_id(cmd.thesis_id)
            if not thesis:
                raise ValueError("Thesis not found")
                
            thesis.invalidate()
            self.repo.save(thesis)
            
            event = ThesisEventFactory.build_invalidated(thesis)
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)),
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)

    def apply_governance_decision(self, cmd: GovernanceDecisionPayload) -> None:
        with self.uow:
            thesis = self.repo.get_by_id(cmd.thesis_id)
            if not thesis:
                raise ValueError("Thesis not found")
                
            if cmd.governance_decision == "APPROVED":
                thesis.activate()
                event = ThesisEventFactory.build_activated(thesis)
            elif cmd.governance_decision == "REJECTED":
                thesis.reject()
                event = ThesisEventFactory.build_rejected(thesis)
            else:
                raise ValueError(f"Unknown decision: {cmd.governance_decision}")
                
            self.repo.save(thesis)
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)),
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)

    def record_review(self, cmd: RecordReviewCommand) -> None:
        with self.uow:
            thesis = self.repo.get_by_id(cmd.thesis_id)
            if not thesis:
                raise ValueError("Thesis not found")
                
            # ADR-12.6 Event-Only Review Workflow: Do not mutate thesis
            event = ThesisEventFactory.build_reviewed(thesis.identity.thesis_id, cmd.review)
            outbox_record = OutboxRecord(
                envelope_id=event.event_id,
                payload=json.dumps(asdict(event)),
                published_status=False
            )
            self.uow.outbox_repository.save(outbox_record)
