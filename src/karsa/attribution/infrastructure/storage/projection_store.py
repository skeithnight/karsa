import json
from typing import List, Dict, Any

class PostgresProjectionStore:
    def __init__(self, connection):
        self.conn = connection

    def upsert(self, source_context_id: str, contributors: List[Dict[str, Any]]):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO attribution_input_projection (source_context_id, contributors) VALUES (%s, %s) ON CONFLICT (source_context_id) DO UPDATE SET contributors=EXCLUDED.contributors",
                   (source_context_id, json.dumps(contributors)))

    def get_by_id(self, source_context_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT contributors FROM attribution_input_projection WHERE source_context_id=%s", (source_context_id,))
        row = cur.fetchone()
        return row[0] if row else []
