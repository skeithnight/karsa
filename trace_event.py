from karsa.app import app
from karsa.bootstrap import ApplicationContainer
from karsa.post_mortem.services import PostMortemService
import uuid

container = ApplicationContainer()

try:
    pm_id = str(uuid.uuid4())
    res = container.pm_service.create_post_mortem(
        postmortem_id=pm_id,
        incident_ref="INC-1234",
        failure_classification={"category": "PROCESS"},
        root_causes=[{"component": "DB", "description": "Failure"}],
        findings=[{"finding": "Something broke"}]
    )
    print(f"Created PM: {res}")
except Exception as e:
    print(f"Error: {e}")

events = getattr(container.event_bus, 'published_events', [])
if not events and not hasattr(container.event_bus, 'published_events'):
    print("MockEventBus swallows events without tracking.")
else:
    print(f"Published events: {len(events)}")
    for e in events:
        print(e)
