from sqlalchemy import text

class PostgresIntelligenceDataMartRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_allocation_readiness(self, date_target=None):
        query = """
            SELECT worker_urn, eligibility_status, cumulative_alpha, max_drawdown, observation_count
            FROM vw_allocation_readiness
        """
        params = {}
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params).fetchall()
            return [{
                "worker_urn": r[0],
                "eligibility_status": r[1] if r[1] else "LIMITED",
                "cumulative_alpha": float(r[2]) if r[2] is not None else 0.0,
                "max_drawdown": float(r[3]) if r[3] is not None else 0.0,
                "observation_count": int(r[4]) if r[4] is not None else 0
            } for r in result]

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
