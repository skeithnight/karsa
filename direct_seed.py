import uuid
import datetime
import json
import psycopg2

def insert_event(cur, stream_id, stream_version, event_type, payload):
    event_id = uuid.uuid4().hex
    record_id = uuid.uuid4().hex
    
    cur.execute("""
        INSERT INTO event_journal (
            id, stream_id, stream_version, event_type, payload, occurred_at,
            aggregate_id, aggregate_type, event_id, schema_version
        ) VALUES (
            %(id)s, %(stream_id)s, %(stream_version)s, %(event_type)s, %(payload)s, %(occurred_at)s,
            %(aggregate_id)s, %(aggregate_type)s, %(event_id)s, %(schema_version)s
        )
    """, {
        "id": record_id,
        "stream_id": stream_id,
        "stream_version": stream_version,
        "event_type": event_type,
        "payload": json.dumps(payload),
        "occurred_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "aggregate_id": stream_id,
        "aggregate_type": "Attribution",
        "event_id": event_id,
        "schema_version": 1
    })

def seed():
    conn = psycopg2.connect("postgresql://karsa:karsa_password@localhost:5432/karsa_db")
    cur = conn.cursor()

    lineage_id = str(uuid.uuid4())
    decision_id = str(uuid.uuid4())
    forecast_id = str(uuid.uuid4())
    
    insert_event(cur, lineage_id, 1, "DecisionLineageCreatedEvent", {
        "lineage_id": lineage_id,
        "decision_id": decision_id,
        "forecast_id": forecast_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    
    node_id = str(uuid.uuid4())
    insert_event(cur, lineage_id, 2, "LineageNodeAddedEvent", {
        "node_id": node_id,
        "lineage_id": lineage_id,
        "capability_id": "cap1",
        "worker_urn": "urn:worker:1",
        "role": "agent"
    })
    
    assessment_id = str(uuid.uuid4())
    fact_id = str(uuid.uuid4())
    
    insert_event(cur, lineage_id, 3, "AttributionFactGeneratedEvent", {
        "assessment_id": assessment_id,
        "lineage_id": lineage_id,
        "fact_id": fact_id,
        "dimensions": {"foo": "bar"}
    })
    
    insert_event(cur, lineage_id, 4, "AttributionAssessmentSealedEvent", {
        "assessment_id": assessment_id,
        "lineage_id": lineage_id,
        "fact_count": 1,
        "provenance_urn": "urn:prov:1"
    })

    conn.commit()
    print("Seeded successfully!")

if __name__ == "__main__":
    seed()
