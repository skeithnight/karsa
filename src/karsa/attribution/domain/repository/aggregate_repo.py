from karsa.attribution.domain.models import AttributionLedger
from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.attribution.domain.events import (
    AttributionCalculatedEvent, CreditAllocatedEvent
)

class AttributionAggregateRepository:
    def __init__(self, journal_repo: EventJournalRepository):
        self.journal = journal_repo
        
        # Register event type mappings
        self.journal._event_types.update({
            "AttributionCalculatedEvent": AttributionCalculatedEvent,
            "CreditAllocatedEvent": CreditAllocatedEvent
        })

    def get(self, attribution_urn: str) -> AttributionLedger:
        events = self.journal.read_events_for_stream(f"AttributionLedger:{attribution_urn}")
        if not events:
            return None
            
        aggregate = AttributionLedger(aggregate_version=0)
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

    def save(self, aggregate: AttributionLedger, expected_version: int):
        events = aggregate.pull_domain_events()
        if not events:
            return
            
        self.journal.append_events(
            aggregate_id=aggregate.aggregate_id,
            aggregate_type=aggregate.aggregate_type,
            events=events,
            expected_version=expected_version
        )
