from typing import Optional
from datetime import datetime
from karsa.firm_intelligence.repository.data_mart_repo import PostgresIntelligenceDataMartRepository
from karsa.firm_intelligence.api.dtos import IntelligenceResponseDTO

class FirmIntelligenceQueryService:
    def __init__(self, repo: PostgresIntelligenceDataMartRepository):
        self.repo = repo
        
    def _get_last_sequence(self):
        with self.repo.engine.connect() as conn:
            res = conn.execute("SELECT last_processed_sequence FROM projection_checkpoints WHERE projection_name = 'firm_intelligence_mart'").fetchone()
            return res[0] if res else 0

    def query_allocation_readiness(self, date_target: Optional[datetime] = None) -> IntelligenceResponseDTO:
        data = self.repo.get_allocation_readiness(date_target)
        seq = self._get_last_sequence()
        return IntelligenceResponseDTO(data=data, last_processed_sequence=seq, generated_at=datetime.utcnow())

    def query_governance_suspensions(self, since: Optional[datetime] = None) -> IntelligenceResponseDTO:
        data = self.repo.get_suspensions(since)
        seq = self._get_last_sequence()
        return IntelligenceResponseDTO(data=data, last_processed_sequence=seq, generated_at=datetime.utcnow())

    def query_swarm_diagnostics(self, urn: str) -> IntelligenceResponseDTO:
        data = self.repo.get_swarm_diagnostics(urn)
        seq = self._get_last_sequence()
        return IntelligenceResponseDTO(data=data, last_processed_sequence=seq, generated_at=datetime.utcnow())
