from datetime import datetime

class DataMartProjectionService:
    def __init__(self, conn):
        self.conn = conn

    def handle(self, event):
        event_type = event.get("event_type", "")
        seq = event.get("global_sequence", 0)
        payload = event.get("payload", {})
        timestamp = event.get("occurred_at", datetime.utcnow())

        print(f"DEBUG: Handling DataMart Event: {event_type} seq: {seq}")

        # Identity dimension SCD2 update helper
        def ensure_worker_dim(urn, stype, ts):
            # Check if active exists
            with self.conn.cursor() as cur:
                cur.execute("SELECT dim_worker_id, subject_type FROM dim_worker WHERE worker_urn = %s AND is_current = true", (urn,))
                result = cur.fetchone()
                if not result:
                    # Insert new
                    cur.execute("INSERT INTO dim_worker (worker_urn, subject_type, effective_from) VALUES (%s, %s, %s) RETURNING dim_worker_id", (urn, stype, ts))
                    return cur.fetchone()[0]
                elif result[1] != stype:
                    # Expire old
                    cur.execute("UPDATE dim_worker SET effective_to = %s, is_current = false WHERE worker_urn = %s AND is_current = true", (ts, urn))
                    # Insert new
                    cur.execute("INSERT INTO dim_worker (worker_urn, subject_type, effective_from) VALUES (%s, %s, %s) RETURNING dim_worker_id", (urn, stype, ts))
                    return cur.fetchone()[0]
                return result[0]

        def get_regime_dim(urn):
            if not urn:
                return None
            with self.conn.cursor() as cur:
                cur.execute("SELECT dim_regime_id FROM dim_regime WHERE regime_urn = %s AND is_current = true", (urn,))
                res = cur.fetchone()
                return res[0] if res else None

        if event_type == "WorkerLifecycleTransitionedEvent":
            w_id = ensure_worker_dim(payload["worker_urn"], payload.get("subject_type", "UNKNOWN"), timestamp)
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO fact_capability_transition (dim_worker_id, old_state, new_state, authority, reason, event_timestamp, event_sequence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_sequence) DO NOTHING
                """, (
                    w_id, payload["old_state"], payload["new_state"],
                    payload["authority"], payload["reason"], timestamp, seq
                ))

        elif event_type == "WorkerAlphaRecordedEvent":
            w_id = ensure_worker_dim(payload["worker_urn"], payload.get("subject_type", "UNKNOWN"), timestamp)
            r_id = get_regime_dim(payload.get("regime_urn"))

            # Step 1: Idempotent fact insert
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO fact_alpha_generation (dim_worker_id, dim_regime_id, alpha_delta, cumulative_alpha, event_timestamp, event_sequence)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_sequence) DO NOTHING
                """, (
                    w_id, r_id, payload["alpha_delta"], payload["cumulative_alpha"], timestamp, seq
                ))
                fact_inserted = cur.rowcount > 0

            # Step 2: Performance upsert — only increment observation_count on new fact
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO projection_worker_performance
                    (worker_id, cumulative_gross_pnl, observation_count, current_drawdown, max_drawdown, high_watermark)
                    VALUES (%s, %s, 1, 0, 0, %s)
                    ON CONFLICT (worker_id) DO UPDATE SET
                        cumulative_gross_pnl = EXCLUDED.cumulative_gross_pnl,
                        observation_count = projection_worker_performance.observation_count + CASE WHEN %s THEN 1 ELSE 0 END,
                        high_watermark = GREATEST(projection_worker_performance.high_watermark, EXCLUDED.cumulative_gross_pnl),
                        current_drawdown = GREATEST(projection_worker_performance.high_watermark, EXCLUDED.cumulative_gross_pnl) - EXCLUDED.cumulative_gross_pnl,
                        max_drawdown = GREATEST(projection_worker_performance.max_drawdown, GREATEST(projection_worker_performance.high_watermark, EXCLUDED.cumulative_gross_pnl) - EXCLUDED.cumulative_gross_pnl)
                """, (
                    payload["worker_urn"], payload["cumulative_alpha"], payload["cumulative_alpha"],
                    fact_inserted,
                ))

        elif event_type == "CreditAllocatedEvent":
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edge_swarm_attribution (parent_worker_urn, child_worker_urn, attribution_urn, skill_ratio, event_sequence)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (event_sequence) DO NOTHING
                """, (
                    payload.get("parent_node_id"), payload["subject_urn"], payload["attribution_urn"],
                    payload["skill_ratio"], seq
                ))
