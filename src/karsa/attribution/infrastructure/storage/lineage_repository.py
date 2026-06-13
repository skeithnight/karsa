from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
from typing import Optional

class PostgresLineageRepository:
    def __init__(self, connection):
        self.conn = connection

    def get_by_id(self, identity: OutcomeSequenceIdentity) -> Optional[AttributionLineage]:
        cur = self.conn.cursor()
        cur.execute("SELECT active_attribution_id, current_generation, version FROM attribution_lineage WHERE outcome_id=%s AND sequence_id=%s", 
                   (identity.outcome_id, identity.sequence_id))
        row = cur.fetchone()
        if not row: return None
        return AttributionLineage(identity, row[0], row[1], row[2])

    def save(self, lineage: AttributionLineage):
        cur = self.conn.cursor()
        if lineage.aggregate_version == 1:
            cur.execute("INSERT INTO attribution_lineage (outcome_id, sequence_id, active_attribution_id, current_generation, version) VALUES (%s, %s, %s, %s, %s)",
                       (lineage.identity.outcome_id, lineage.identity.sequence_id, lineage.active_attribution_id, lineage.current_generation, lineage.aggregate_version))
        else:
            cur.execute("UPDATE attribution_lineage SET active_attribution_id=%s, current_generation=%s, version=%s WHERE outcome_id=%s AND sequence_id=%s AND version=%s",
                       (lineage.active_attribution_id, lineage.current_generation, lineage.aggregate_version, lineage.identity.outcome_id, lineage.identity.sequence_id, lineage.aggregate_version - 1))
            if cur.rowcount == 0:
                raise ConcurrencyConflictError(f"Concurrency conflict on lineage {lineage.identity}")
