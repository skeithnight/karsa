import uuid
import psycopg
from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.attribution.infrastructure.repositories import AttributionRepository
from karsa.attribution.application.service import AttributionLineageService, AttributionAssessmentService

# Setup DB connection
conn = psycopg.connect("postgresql://karsa:karsa_password@localhost:5432/karsa_db")
journal = EventJournalRepository(conn)
# Provide dummy repo since read paths are not hit in the write flow
dummy_repo = AttributionRepository(conn)

lineage_svc = AttributionLineageService(journal, dummy_repo)
assessment_svc = AttributionAssessmentService(journal, dummy_repo)

# Workflow
decision_id = str(uuid.uuid4())
forecast_id = str(uuid.uuid4())
lineage_id = lineage_svc.create_lineage(decision_id, forecast_id)
node_id = lineage_svc.add_lineage_node(lineage_id, "cap-1", "worker-1", "role-1")

assessment_id = str(uuid.uuid4())
fact_id = assessment_svc.generate_fact(lineage_id, assessment_id, {"val": 1})
assessment_svc.seal_assessment(assessment_id, lineage_id, [fact_id], "urn:test")

conn.commit()

# Verify
with conn.cursor() as cur:
    cur.execute("SELECT stream_id, stream_version, event_type FROM event_journal WHERE stream_id IN (%s, %s) ORDER BY stream_id, stream_version", (lineage_id, assessment_id))
    rows = cur.fetchall()
    print("VERIFICATION RESULT:")
    for r in rows:
        print(f"stream_id={r[0]}, version={r[1]}, type={r[2]}")

# OCC Validation
print("OCC VALIDATION:")
try:
    from karsa.attribution.events.events import DecisionLineageCreatedEvent
    event = DecisionLineageCreatedEvent()
    event.stream_id = lineage_id
    journal.append(event, stream_version=1) # Already used by create_lineage!
    conn.commit()
    print("OCC FAILED - Allowed duplicate version")
except psycopg.errors.UniqueViolation as e:
    print(f"OCC PASSED - Caught UniqueViolation: {e}")
    conn.rollback()

