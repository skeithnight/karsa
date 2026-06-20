import json
from sqlalchemy import text
from karsa.projections.base_projection import BaseProjection

class ThesisIntelligenceProjectionService(BaseProjection):
    def get_events(self) -> list[str]:
        return [
            "ThesisProposedEvent",
            "ThesisActivatedEvent",
            "ThesisChallengedEvent",
            "ThesisRefinedEvent",
            "ThesisInvalidatedEvent",
            "ThesisRetiredEvent"
        ]

    def handle(self, event: dict, connection):
        event_type = event["event_type"]
        payload = event["payload"]
        metadata = event.get("metadata", {})
        
        thesis_urn = payload["thesis_urn"]
        stream_version = event["stream_version"]
        event_id = event["event_id"]
        causation_id = metadata.get("causation_id")
        correlation_id = metadata.get("correlation_id")
        actor_urn = metadata.get("actor_urn")
        rationale = metadata.get("rationale")
        timestamp = event["timestamp"]

        confidence = float(payload.get("confidence", 0.0))
        lifecycle_state = payload.get("state", "UNKNOWN")
        assumptions = payload.get("assumptions", [])

        # Materialize thesis_timeline
        connection.execute(
            text("""
                INSERT INTO thesis_timeline (
                    event_id, thesis_urn, stream_version, causation_id, correlation_id,
                    actor_urn, rationale, event_type, timestamp
                ) VALUES (
                    :event_id, :thesis_urn, :stream_version, :causation_id, :correlation_id,
                    :actor_urn, :rationale, :event_type, :timestamp
                ) ON CONFLICT (thesis_urn, stream_version) DO NOTHING
            """),
            {
                "event_id": event_id, "thesis_urn": thesis_urn, "stream_version": stream_version,
                "causation_id": causation_id, "correlation_id": correlation_id,
                "actor_urn": actor_urn, "rationale": rationale, "event_type": event_type,
                "timestamp": timestamp
            }
        )

        # Calculate previous confidence
        prev_conf_row = connection.execute(
            text("SELECT new_confidence FROM confidence_history WHERE thesis_urn = :urn ORDER BY stream_version DESC LIMIT 1"),
            {"urn": thesis_urn}
        ).fetchone()
        previous_confidence = prev_conf_row[0] if prev_conf_row else confidence
        delta = confidence - previous_confidence

        # Materialize confidence_history
        connection.execute(
            text("""
                INSERT INTO confidence_history (
                    id, thesis_urn, stream_version, previous_confidence, new_confidence,
                    delta, rationale, event_type, causation_id, timestamp
                ) VALUES (
                    gen_random_uuid(), :thesis_urn, :stream_version, :prev, :new,
                    :delta, :rationale, :event_type, :causation_id, :timestamp
                ) ON CONFLICT (thesis_urn, stream_version) DO NOTHING
            """),
            {
                "thesis_urn": thesis_urn, "stream_version": stream_version,
                "prev": previous_confidence, "new": confidence, "delta": delta,
                "rationale": rationale, "event_type": event_type, "causation_id": causation_id,
                "timestamp": timestamp
            }
        )

        # Handle assumption logic
        total_assumptions = len(assumptions)
        valid_assumptions = 0
        challenged_assumptions = 0
        invalid_assumptions = 0

        for a in assumptions:
            a_urn = a["urn"]
            statement = a["statement"]
            is_valid = a.get("is_valid", True)
            
            if is_valid:
                valid_assumptions += 1
            else:
                invalid_assumptions += 1

            # Fetch previous state
            prev_a = connection.execute(
                text("SELECT statement, is_valid, challenge_count FROM assumption_snapshots WHERE assumption_urn = :urn"),
                {"urn": a_urn}
            ).fetchone()

            challenge_count = prev_a[2] if prev_a else 0
            changed = False
            if not prev_a:
                changed = True
            elif prev_a[1] != is_valid or prev_a[0] != statement:
                changed = True
                if not is_valid and prev_a[1]:
                    challenge_count += 1

            if changed:
                connection.execute(
                    text("""
                        INSERT INTO assumption_snapshots (assumption_urn, thesis_urn, statement, is_valid, challenge_count)
                        VALUES (:urn, :thesis, :stmt, :valid, :count)
                        ON CONFLICT (assumption_urn) DO UPDATE SET
                            statement = EXCLUDED.statement,
                            is_valid = EXCLUDED.is_valid,
                            challenge_count = EXCLUDED.challenge_count
                    """),
                    {"urn": a_urn, "thesis": thesis_urn, "stmt": statement, "valid": is_valid, "count": challenge_count}
                )
                
                connection.execute(
                    text("""
                        INSERT INTO assumption_timeline (event_id, assumption_urn, event_type, actor_urn, rationale, timestamp)
                        VALUES (:event_id, :urn, :event_type, :actor, :rat, :ts)
                        ON CONFLICT DO NOTHING
                    """),
                    {"event_id": event_id, "urn": a_urn, "event_type": event_type, "actor": actor_urn, "rat": rationale, "ts": timestamp}
                )

        # Handle health projection
        health_score = (valid_assumptions / total_assumptions) * 100 if total_assumptions > 0 else 100.0
        health_status = 'RED'
        if health_score >= 80:
            health_status = 'GREEN'
        elif health_score >= 50:
            health_status = 'YELLOW'

        connection.execute(
            text("""
                INSERT INTO thesis_health_snapshots (
                    thesis_urn, lifecycle_state, confidence, total_assumptions,
                    valid_assumptions, challenged_assumptions, invalid_assumptions,
                    health_score, health_status, snapshot_version
                ) VALUES (
                    :urn, :state, :conf, :total, :valid, :chal, :inv, :score, :status, :version
                ) ON CONFLICT (thesis_urn) DO UPDATE SET
                    lifecycle_state = EXCLUDED.lifecycle_state,
                    confidence = EXCLUDED.confidence,
                    total_assumptions = EXCLUDED.total_assumptions,
                    valid_assumptions = EXCLUDED.valid_assumptions,
                    challenged_assumptions = EXCLUDED.challenged_assumptions,
                    invalid_assumptions = EXCLUDED.invalid_assumptions,
                    health_score = EXCLUDED.health_score,
                    health_status = EXCLUDED.health_status,
                    snapshot_version = EXCLUDED.snapshot_version
            """),
            {
                "urn": thesis_urn, "state": lifecycle_state, "conf": confidence,
                "total": total_assumptions, "valid": valid_assumptions, "chal": challenged_assumptions,
                "inv": invalid_assumptions, "score": health_score, "status": health_status,
                "version": stream_version
            }
        )
