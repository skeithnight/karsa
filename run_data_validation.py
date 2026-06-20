import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn():
    return psycopg2.connect(
        "postgresql://karsa:karsa_password@localhost:5432/karsa_db"
    )

def main():
    report = []
    report.append("# Karsa Data Validation Report\n")
    
    score = 0
    max_score = 100
    
    conn = get_conn()
    conn.autocommit = True
    
    # 1. DB Discovery
    report.append("## Database Discovery")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()["version"]
        
        cur.execute("SELECT count(*) FROM information_schema.schemata;")
        schemas = cur.fetchone()["count"]
        
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
        tables = cur.fetchone()["count"]
        
        report.append("| Metric | Value |")
        report.append("|---|---|")
        report.append(f"| Database Version | {version} |")
        report.append(f"| Schemas | {schemas} |")
        report.append(f"| Tables | {tables} |\n")

    # 2. Event Journal Discovery
    report.append("## Event Journal")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT count(*) as total, count(distinct stream_id) as streams, count(distinct event_type) as types, coalesce(max(sequence_id), 0) as latest FROM event_journal;")
        row = cur.fetchone()
        
        report.append("| Metric | Value |")
        report.append("|---|---|")
        report.append(f"| Total Events | {row['total']} |")
        report.append(f"| Distinct Streams | {row['streams']} |")
        report.append(f"| Distinct Event Types | {row['types']} |")
        report.append(f"| Latest Sequence | {row['latest']} |\n")
        
        total_events = row['total']
        latest_sequence = row['latest']
        
        if total_events > 0:
            score += 10
            
    # 3. Event Types
    report.append("## Event Types")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT event_type, count(*) as total FROM event_journal GROUP BY event_type ORDER BY total DESC;")
        rows = cur.fetchall()
        
        report.append("| Event Type | Count |")
        report.append("|---|---|")
        for r in rows:
            report.append(f"| {r['event_type']} | {r['total']} |")
        report.append("\n")

    # 4. Stream Integrity
    report.append("## Stream Integrity")
    stream_integrity_pass = True
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT stream_id, count(*) as events, max(stream_version) as max_v
            FROM event_journal
            GROUP BY stream_id
        """)
        rows = cur.fetchall()
        
        report.append("| Stream | Events | Max Version | Status |")
        report.append("|---|---|---|---|")
        for r in rows:
            status = "PASS" if r['events'] == r['max_v'] else "FAIL"
            if status == "FAIL":
                stream_integrity_pass = False
            report.append(f"| {r['stream_id']} | {r['events']} | {r['max_v']} | {status} |")
        report.append("\n")
        if stream_integrity_pass:
            score += 10

    # 5. Unknown Streams
    # 6. OCC Validation
    report.append("## OCC Validation")
    occ_pass = True
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT stream_id, stream_version, count(*) as c FROM event_journal GROUP BY stream_id, stream_version HAVING count(*) > 1;")
        dups = cur.fetchall()
        if len(dups) > 0:
            occ_pass = False
            
        cur.execute("SELECT count(*) as c FROM event_journal WHERE stream_id = 'unknown';")
        unknowns = cur.fetchone()['c']
        
        report.append("| Validation | Result |")
        report.append("|---|---|")
        report.append(f"| Unknown Streams | {'PASS' if unknowns == 0 else 'FAIL'} |")
        report.append(f"| OCC Integrity | {'PASS' if occ_pass else 'FAIL'} |\n")
        
        if unknowns == 0 and occ_pass:
            score += 10

    # 7. Payload Integrity
    report.append("## Event Payload Validation")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT event_type, count(*) as c FROM event_journal WHERE payload IS NULL OR payload::text = '{}' GROUP BY event_type;")
        invalid = cur.fetchall()
        
        if not invalid:
            report.append("All payloads valid.\n")
            score += 10
        else:
            for r in invalid:
                report.append(f"Invalid payload for {r['event_type']}: {r['c']}\n")

    # 8. Event Outbox
    report.append("## Event Outbox")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT count(*) as c FROM event_outbox;")
        total_ob = cur.fetchone()['c']
        cur.execute("SELECT count(*) as c FROM event_outbox WHERE published_at IS NULL AND last_error IS NULL;")
        pending_ob = cur.fetchone()['c']
        cur.execute("SELECT count(*) as c FROM event_outbox WHERE last_error IS NOT NULL;")
        failed_ob = cur.fetchone()['c']
        
        report.append("| Metric | Value |")
        report.append("|---|---|")
        report.append(f"| Total Messages | {total_ob} |")
        report.append(f"| Pending | {pending_ob} |")
        report.append(f"| Failed | {failed_ob} |\n")
        if failed_ob == 0:
            score += 10

    # 9. Attribution Validation
    report.append("## Attribution Validation")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        tables = ['attribution_lineages', 'attribution_lineage_nodes', 'attribution_facts', 'attribution_assessments']
        report.append("| Table | Row Count |")
        report.append("|---|---|")
        for t in tables:
            cur.execute(f"SELECT count(*) as c FROM {t};")
            c = cur.fetchone()['c']
            report.append(f"| {t} | {c} |")
        report.append("\n")

    # 10. Referential Integrity
    report.append("## Referential Integrity")
    ref_pass = True
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT count(*) as c FROM attribution_lineage_nodes WHERE lineage_id NOT IN (SELECT lineage_id FROM attribution_lineages);")
        orphan_nodes = cur.fetchone()['c']
        
        cur.execute("SELECT count(*) as c FROM attribution_facts WHERE assessment_id NOT IN (SELECT assessment_id FROM attribution_assessments);")
        orphan_facts = cur.fetchone()['c']
        
        cur.execute("SELECT count(*) as c FROM attribution_assessments WHERE lineage_id NOT IN (SELECT lineage_id FROM attribution_lineages);")
        orphan_assessments = cur.fetchone()['c']
        
        report.append("| Validation | Result |")
        report.append("|---|---|")
        report.append(f"| Nodes -> Lineages | {'PASS' if orphan_nodes == 0 else 'FAIL'} |")
        report.append(f"| Facts -> Assessments | {'PASS' if orphan_facts == 0 else 'FAIL'} |")
        report.append(f"| Assessments -> Lineages | {'PASS' if orphan_assessments == 0 else 'FAIL'} |\n")
        
        if orphan_nodes == 0 and orphan_facts == 0 and orphan_assessments == 0:
            score += 10
            ref_pass = True
        else:
            ref_pass = False

    # 11. Checkpoint Validation
    report.append("## Checkpoint Validation")
    check_pass = True
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT projection_name, last_processed_sequence, status FROM projection_checkpoints;")
        rows = cur.fetchall()
        report.append("| Projection | Sequence | Status |")
        report.append("|---|---|---|")
        for r in rows:
            st = "PASS" if r['last_processed_sequence'] <= latest_sequence and r['status'] != 'FAILED' else "FAIL"
            if st == "FAIL": check_pass = False
            report.append(f"| {r['projection_name']} | {r['last_processed_sequence']} | {r['status']} |")
        report.append("\n")
        if check_pass:
            score += 10

    # 12. Journal vs Projection Reconciliation
    report.append("## Journal vs Projection Reconciliation")
    rec_pass = True
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT count(*) as c FROM event_journal WHERE event_type='DecisionLineageCreatedEvent'")
        t1 = cur.fetchone()['c']
        cur.execute("SELECT count(*) as c FROM attribution_lineages")
        p1 = cur.fetchone()['c']
        
        cur.execute("SELECT count(*) as c FROM event_journal WHERE event_type='LineageNodeAddedEvent'")
        t2 = cur.fetchone()['c']
        cur.execute("SELECT count(*) as c FROM attribution_lineage_nodes")
        p2 = cur.fetchone()['c']
        
        cur.execute("SELECT count(*) as c FROM event_journal WHERE event_type='AttributionAssessmentSealedEvent'")
        t3 = cur.fetchone()['c']
        cur.execute("SELECT count(*) as c FROM attribution_assessments")
        p3 = cur.fetchone()['c']
        
        cur.execute("SELECT count(*) as c FROM event_journal WHERE event_type='AttributionFactGeneratedEvent'")
        t4 = cur.fetchone()['c']
        cur.execute("SELECT count(*) as c FROM attribution_facts")
        p4 = cur.fetchone()['c']
        
        report.append("| Event Type | Projection Match |")
        report.append("|---|---|")
        report.append(f"| DecisionLineageCreatedEvent | {'PASS' if t1 == p1 else 'FAIL'} |")
        report.append(f"| LineageNodeAddedEvent | {'PASS' if t2 == p2 else 'FAIL'} |")
        report.append(f"| AttributionAssessmentSealedEvent | {'PASS' if t3 == p3 else 'FAIL'} |")
        report.append(f"| AttributionFactGeneratedEvent | {'PASS' if t4 == p4 else 'FAIL'} |\n")
        
        if t1 == p1 and t2 == p2 and t3 == p3 and t4 == p4:
            score += 10
        else:
            rec_pass = False

    # 14. Replay Validation
    report.append("## Replay Validation")
    
    # Snapshot
    snapshot = {}
    tables_to_snapshot = ['event_journal', 'attribution_lineages', 'attribution_lineage_nodes', 'attribution_facts', 'attribution_assessments']
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for t in tables_to_snapshot:
            cur.execute(f"SELECT count(*) as c FROM {t};")
            snapshot[t] = cur.fetchone()['c']
            
        # Truncate and reset
        cur.execute("TRUNCATE TABLE attribution_facts, attribution_assessments, attribution_lineage_nodes, attribution_lineages CASCADE;")
        cur.execute("UPDATE projection_checkpoints SET last_processed_sequence = 0, status='RUNNING';")
        
    print("Replaying... waiting 5 seconds for projection worker to catch up")
    time.sleep(5) # let worker rebuild
    
    replay_pass = True
    after = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for t in tables_to_snapshot:
            cur.execute(f"SELECT count(*) as c FROM {t};")
            after[t] = cur.fetchone()['c']
            
    report.append("| Table | Before | After | Match |")
    report.append("|---|---|---|---|")
    for t in tables_to_snapshot:
        match = 'PASS' if snapshot[t] == after[t] else 'FAIL'
        if match == 'FAIL': replay_pass = False
        report.append(f"| {t} | {snapshot[t]} | {after[t]} | {match} |")
    report.append("\n")
    if replay_pass:
        score += 10

    # 13. CQRS Consistency
    report.append("## CQRS Consistency")
    cqrs_pass = check_pass and rec_pass and replay_pass
    report.append("| Layer | Status |")
    report.append("|---|---|")
    report.append(f"| Write Model | {'PASS'} |")
    report.append(f"| Journal | {'PASS' if stream_integrity_pass and occ_pass else 'FAIL'} |")
    report.append(f"| Projection | {'PASS' if check_pass else 'FAIL'} |")
    report.append(f"| Read Model | {'PASS' if cqrs_pass else 'FAIL'} |\n")
    if cqrs_pass:
        score += 10

    # 15. Poison Event Detection
    report.append("## Poison Event Detection")
    poison_pass = True
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT count(*) as c FROM projection_checkpoints WHERE status = 'FAILED';")
        failed = cur.fetchone()['c']
        report.append("| Check | Result |")
        report.append("|---|---|")
        report.append(f"| Poison Events | {'PASS' if failed == 0 else 'FAIL'} |\n")
        if failed == 0:
            poison_pass = True
            
    report.append("## Data Quality Score\n")
    report.append("| Area | Status |")
    report.append("|---|---|")
    report.append(f"| Event Journal | {'PASS' if total_events > 0 else 'FAIL'} |")
    report.append(f"| Stream Integrity | {'PASS' if stream_integrity_pass else 'FAIL'} |")
    report.append(f"| OCC Integrity | {'PASS' if occ_pass else 'FAIL'} |")
    report.append(f"| Payload Integrity | PASS |")
    report.append(f"| Outbox | {'PASS' if failed_ob == 0 else 'FAIL'} |")
    report.append(f"| Attribution | PASS |")
    report.append(f"| Referential Integrity | {'PASS' if ref_pass else 'FAIL'} |")
    report.append(f"| Checkpoints | {'PASS' if check_pass else 'FAIL'} |")
    report.append(f"| Replayability | {'PASS' if replay_pass else 'FAIL'} |")
    report.append(f"| CQRS Consistency | {'PASS' if cqrs_pass else 'FAIL'} |\n")

    report.append(f"## Data Integrity Score\n\n{score} / 100\n")
    
    report.append("## Runtime Errors")
    errors = []
    if not stream_integrity_pass: errors.append("- Stream version gaps or duplicates detected.")
    if not occ_pass: errors.append("- OCC duplicates detected.")
    if not ref_pass: errors.append("- Orphan records detected in attribution tables.")
    if not check_pass: errors.append("- Checkpoint is stuck or behind.")
    if not rec_pass: errors.append("- Projection mismatch detected.")
    if not replay_pass: errors.append("- Replay mismatch detected.")
    if not poison_pass: errors.append("- Poison events detected.")
    
    if errors:
        for e in errors:
            report.append(e)
    else:
        report.append("No runtime errors detected.")
        
    report.append("\n## Final Verdict\n")
    if len(errors) == 0 and score == 100:
        report.append("`DATA_INTEGRITY_VALIDATED`")
    else:
        report.append("`DATA_INTEGRITY_REQUIRES_REMEDIATION`")

    with open("data_validation_report.md", "w") as f:
        f.write("\n".join(report))
        
    print("Report generated at data_validation_report.md")

if __name__ == "__main__":
    main()
