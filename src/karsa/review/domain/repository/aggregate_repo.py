from karsa.review.domain.models import ReviewAssessment
from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.review.domain.events import (
    ReviewInitiatedEvent, EvidenceAttachedEvent, CalibrationGradedEvent, ReviewSealedEvent
)

class ReviewAggregateRepository:
    def __init__(self, journal_repo: EventJournalRepository):
        self.journal = journal_repo
        
        # Register event type mappings
        self.journal._event_types.update({
            "ReviewInitiatedEvent": ReviewInitiatedEvent,
            "EvidenceAttachedEvent": EvidenceAttachedEvent,
            "CalibrationGradedEvent": CalibrationGradedEvent,
            "ReviewSealedEvent": ReviewSealedEvent
        })

    def get(self, review_urn: str) -> ReviewAssessment:
        events = self.journal.read_events_for_stream(f"ReviewAssessment:{review_urn}")
        if not events:
            return None
            
        aggregate = ReviewAssessment(aggregate_version=0)
        for event in events:
            # Rehydrate the event object
            event_type = event["event_type"]
            event_cls = self.journal._event_types.get(event_type)
            if event_cls:
                # Instantiate empty event and populate payload
                ev_obj = event_cls.__new__(event_cls)
                ev_obj.payload = event["payload"]
                aggregate.apply_event(ev_obj)
                
        # The version is updated by apply_event, but it must match stream version
        aggregate.aggregate_version = events[-1]["stream_version"]
        aggregate._version = aggregate.aggregate_version
        return aggregate

    def save(self, aggregate: ReviewAssessment, expected_version: int):
        events = aggregate.pull_domain_events()
        if not events:
            return
            
        self.journal.append_events(
            aggregate_id=aggregate.aggregate_id,
            aggregate_type=aggregate.aggregate_type,
            events=events,
            expected_version=expected_version
        )
