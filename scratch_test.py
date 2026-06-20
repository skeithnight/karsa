import uuid
import sys
from karsa.bootstrap import get_postgres_pool
from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.thesis.domain.events import ThesisProposedEvent, ThesisActivatedEvent
from karsa.thesis.application.services import ThesisLifecycleService
from karsa.thesis.domain.models import Thesis
from karsa.thesis.domain.value_objects import LifecycleState

def main():
    pool = get_postgres_pool()
    with pool.connection() as conn:
        journal = EventJournalRepository(conn)
        svc = ThesisLifecycleService(journal)
        
        thesis_urn = f"urn:karsa:thesis:{uuid.uuid4()}"
        snapshot_urn = f"urn:karsa:snapshot:{uuid.uuid4()}"
        
        # 1. Propose (we'll just append it directly for testing since service only has activate)
        proposed = ThesisProposedEvent(
            correlation_id="test-corr",
            causation_id="test-caus",
            stream_version=1,
            payload={"thesis_urn": thesis_urn, "snapshot_urn": snapshot_urn}
        )
        proposed.aggregate_id = thesis_urn
        proposed.aggregate_type = "Thesis"
        proposed.stream_id = f"Thesis:{thesis_urn}"
        
        journal.append_events(f"Thesis:{thesis_urn}", [proposed], 0)
        
        # 2. Activate via service
        new_snapshot = f"urn:karsa:snapshot:{uuid.uuid4()}"
        thesis = svc.activate_thesis(thesis_urn, "caus-2", "corr-2", new_snapshot)
        
        conn.commit()
        print(f"Successfully generated events for {thesis_urn}")

if __name__ == "__main__":
    main()
