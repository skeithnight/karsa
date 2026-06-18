import json

class AttributionProjectionService:
    def __init__(self, connection):
        self.conn = connection

    def consume_decision_lineage_created(self, payload: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO attribution_lineages (lineage_id, decision_id, forecast_id, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (lineage_id) DO NOTHING
            """,
            (payload['lineage_id'], payload['decision_id'], payload['forecast_id'], payload['created_at'])
        )

    def consume_lineage_node_added(self, payload: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO attribution_lineage_nodes (node_id, lineage_id, capability_id, worker_urn, role)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (node_id) DO NOTHING
            """,
            (payload['node_id'], payload['lineage_id'], payload['capability_id'], payload['worker_urn'], payload['role'])
        )

    def consume_attribution_fact_generated(self, payload: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO attribution_assessments (assessment_id, lineage_id, fact_count, provenance_urn)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (assessment_id) DO NOTHING
            """,
            (payload['assessment_id'], payload['lineage_id'], 0, 'pending')
        )
        dims = json.dumps(payload['dimensions'])
        cur.execute(
            """
            INSERT INTO attribution_facts (fact_id, assessment_id, dimensions)
            VALUES (%s, %s, %s)
            ON CONFLICT (fact_id) DO NOTHING
            """,
            (payload['fact_id'], payload['assessment_id'], dims)
        )

    def consume_attribution_assessment_sealed(self, payload: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO attribution_assessments (assessment_id, lineage_id, fact_count, provenance_urn)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (assessment_id) DO UPDATE 
            SET fact_count = EXCLUDED.fact_count, provenance_urn = EXCLUDED.provenance_urn
            """,
            (payload['assessment_id'], payload['lineage_id'], payload['fact_count'], payload['provenance_urn'])
        )
