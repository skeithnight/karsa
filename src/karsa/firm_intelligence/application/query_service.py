from typing import Optional
from datetime import datetime
from karsa.firm_intelligence.repository.data_mart_repo import PostgresIntelligenceDataMartRepository
from karsa.firm_intelligence.api.dtos import IntelligenceResponseDTO

from sqlalchemy import text

class FirmIntelligenceQueryService:
    def __init__(self, repo: PostgresIntelligenceDataMartRepository):
        self.repo = repo
        
    def _get_last_sequence(self):
        with self.repo.engine.connect() as conn:
            res = conn.execute(text("SELECT last_processed_sequence FROM projection_checkpoints WHERE projection_name = 'portfolio_read_models'")).fetchone()
            return res[0] if res else 0

    def query_allocation_readiness(self, date_target: Optional[datetime] = None) -> IntelligenceResponseDTO:
        data = self.repo.get_allocation_readiness(date_target)
        
        # Apply Allocation Ranking Formula
        for row in data:
            reward = row["cumulative_alpha"]
            risk = row["max_drawdown"] * 1.5
            row["ranking_explanation"] = {
                "reward_factor": reward,
                "risk_penalty": risk,
                "final_score": reward - risk
            }
            
        # Sort by final_score DESC, observation_count DESC, max_drawdown ASC, worker_urn ASC
        data.sort(key=lambda x: (
            x["ranking_explanation"]["final_score"],
            x["observation_count"],
            -x["max_drawdown"],
            x["worker_urn"]
        ), reverse=True)
        
        # Note: -max_drawdown with reverse=True means ASC sorting for max_drawdown, worker_urn should be ASC, so we need to handle that carefully
        # Actually, let's sort normally and not use reverse=True for the complex ones
        data.sort(key=lambda x: (
            -x["ranking_explanation"]["final_score"],
            -x["observation_count"],
            x["max_drawdown"],
            x["worker_urn"]
        ))
        
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
