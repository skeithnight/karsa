from sqlalchemy import text
from datetime import datetime

class DataMartProjectionService:
    def handle(self, event, conn):
        event_type = event["event_type"]
        seq = event["global_sequence"]
        payload = event["payload"]
        timestamp = event["created_at"]
        
        # Identity dimension SCD2 update helper
        def ensure_worker_dim(urn, stype, ts):
            # Check if active exists
            result = conn.execute(text("SELECT dim_worker_id, subject_type FROM dim_worker WHERE worker_urn = :u AND is_current = true"), {"u": urn}).fetchone()
            if not result:
                # Insert new
                res = conn.execute(text("INSERT INTO dim_worker (worker_urn, subject_type, effective_from) VALUES (:u, :t, :ts) RETURNING dim_worker_id"), {"u": urn, "t": stype, "ts": ts})
                return res.fetchone()[0]
            elif result[1] != stype:
                # Expire old
                conn.execute(text("UPDATE dim_worker SET effective_to = :ts, is_current = false WHERE worker_urn = :u AND is_current = true"), {"ts": ts, "u": urn})
                # Insert new
                res = conn.execute(text("INSERT INTO dim_worker (worker_urn, subject_type, effective_from) VALUES (:u, :t, :ts) RETURNING dim_worker_id"), {"u": urn, "t": stype, "ts": ts})
                return res.fetchone()[0]
            return result[0]
            
        def get_regime_dim(urn):
            if not urn:
                return None
            res = conn.execute(text("SELECT dim_regime_id FROM dim_regime WHERE regime_urn = :u AND is_current = true"), {"u": urn}).fetchone()
            return res[0] if res else None

        if event_type == "WorkerLifecycleTransitionedEvent":
            w_id = ensure_worker_dim(payload["worker_urn"], payload.get("subject_type", "UNKNOWN"), timestamp)
            try:
                conn.execute(text("""
                    INSERT INTO fact_capability_transition (dim_worker_id, old_state, new_state, authority, reason, event_timestamp, event_sequence)
                    VALUES (:w, :os, :ns, :auth, :rsn, :ts, :seq)
                """), {
                    "w": w_id, "os": payload["old_state"], "ns": payload["new_state"], 
                    "auth": payload["authority"], "rsn": payload["reason"], "ts": timestamp, "seq": seq
                })
            except Exception as e:
                # Ignore duplicate sequence
                if "uq_fact_capability_event_sequence" not in str(e):
                    raise
                    
        elif event_type == "WorkerAlphaRecordedEvent":
            w_id = ensure_worker_dim(payload["worker_urn"], payload.get("subject_type", "UNKNOWN"), timestamp)
            r_id = get_regime_dim(payload.get("regime_urn"))
            try:
                conn.execute(text("""
                    INSERT INTO fact_alpha_generation (dim_worker_id, dim_regime_id, alpha_delta, cumulative_alpha, event_timestamp, event_sequence)
                    VALUES (:w, :r, :d, :c, :ts, :seq)
                """), {
                    "w": w_id, "r": r_id, "d": payload["alpha_delta"], "c": payload["cumulative_alpha"], "ts": timestamp, "seq": seq
                })
            except Exception as e:
                if "uq_fact_alpha_event_sequence" not in str(e):
                    raise
                    
        elif event_type == "CreditAllocatedEvent":
            try:
                conn.execute(text("""
                    INSERT INTO edge_swarm_attribution (parent_worker_urn, child_worker_urn, attribution_urn, skill_ratio, event_sequence)
                    VALUES (:p, :c, :a, :sr, :seq)
                """), {
                    "p": payload.get("parent_node_id"), "c": payload["subject_urn"], "a": payload["attribution_urn"],
                    "sr": payload["skill_ratio"], "seq": seq
                })
            except Exception as e:
                if "uq_edge_swarm_event_sequence" not in str(e):
                    raise
