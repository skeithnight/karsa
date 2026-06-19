from sqlalchemy import text

class PostgresIntelligenceDataMartRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_allocation_readiness(self, date_target=None):
        # Sample logic for querying facts
        # Real implementation would join fact_capability_transition, fact_alpha_generation, etc.
        query = """
            SELECT w.worker_urn, w.subject_type, f.alpha_delta, r.regime_type
            FROM fact_alpha_generation f
            JOIN dim_worker w ON f.dim_worker_id = w.dim_worker_id
            LEFT JOIN dim_regime r ON f.dim_regime_id = r.dim_regime_id
        """
        params = {}
        if date_target:
            query += " WHERE f.event_timestamp <= :dt AND w.effective_from <= :dt AND w.effective_to > :dt"
            params["dt"] = date_target
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params).fetchall()
            return [{"worker_urn": r[0], "subject_type": r[1], "alpha_delta": r[2], "regime_type": r[3]} for r in result]

    def get_suspensions(self, since=None):
        query = """
            SELECT worker_urn, old_state, new_state, authority, reason, event_timestamp
            FROM vw_governance_suspension_audit
        """
        params = {}
        if since:
            query += " WHERE event_timestamp >= :since"
            params["since"] = since
            
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params).fetchall()
            return [{"worker_urn": r[0], "old_state": r[1], "new_state": r[2], "authority": r[3], "reason": r[4], "event_timestamp": r[5]} for r in result]

    def get_swarm_diagnostics(self, urn: str):
        query = """
            WITH RECURSIVE swarm_tree AS (
                SELECT parent_worker_urn, child_worker_urn, skill_ratio
                FROM edge_swarm_attribution
                WHERE parent_worker_urn = :urn
                UNION ALL
                SELECT e.parent_worker_urn, e.child_worker_urn, e.skill_ratio
                FROM edge_swarm_attribution e
                JOIN swarm_tree st ON e.parent_worker_urn = st.child_worker_urn
            )
            SELECT * FROM swarm_tree;
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"urn": urn}).fetchall()
            return [{"parent_worker_urn": r[0], "child_worker_urn": r[1], "skill_ratio": r[2]} for r in result]
