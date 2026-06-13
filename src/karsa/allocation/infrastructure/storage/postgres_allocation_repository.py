import json
from typing import Optional
from psycopg_pool import ConnectionPool

from karsa.allocation.domain.repository.allocation_repository import AllocationRepository
from karsa.allocation.domain.model.allocation import RiskAllocation
from karsa.allocation.infrastructure.storage.allocation_mapper import AllocationMapper
from karsa.allocation.infrastructure.storage.allocation_records import (
    RiskAllocationRecord, RiskBudgetRecord, LiquidityConstraintRecord
)

class PostgresAllocationRepository(AllocationRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _setup_schema(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS risk_allocation (
                        allocation_id VARCHAR(255) PRIMARY KEY,
                        thesis_id VARCHAR(255) NOT NULL,
                        state VARCHAR(50) NOT NULL,
                        risk_budget JSONB NOT NULL
                    );
                """)
            conn.commit()

    def save(self, allocation: RiskAllocation) -> None:
        record = AllocationMapper.to_record(allocation)
        
        liquidity_dict = {
            "max_adv_participation": record.risk_budget.liquidity_constraint.max_adv_participation,
            "max_days_to_liquidate": record.risk_budget.liquidity_constraint.max_days_to_liquidate
        }
        
        budget_dict = {
            "volatility_budget": record.risk_budget.volatility_budget,
            "drawdown_limit": record.risk_budget.drawdown_limit,
            "liquidity_constraint": liquidity_dict
        }
        
        budget_json = json.dumps(budget_dict)
        
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO risk_allocation (
                        allocation_id, thesis_id, state, risk_budget
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (allocation_id) DO UPDATE SET
                        state = EXCLUDED.state,
                        risk_budget = EXCLUDED.risk_budget;
                """, (
                    record.allocation_id,
                    record.thesis_id,
                    record.state,
                    budget_json
                ))
            conn.commit()

    def get_by_id(self, allocation_id: str) -> Optional[RiskAllocation]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT allocation_id, thesis_id, state, risk_budget FROM risk_allocation WHERE allocation_id = %s", (allocation_id,))
                row = cur.fetchone()
                
        if not row:
            return None
            
        b_data = row[3]
        liquidity = LiquidityConstraintRecord(
            max_adv_participation=b_data["liquidity_constraint"]["max_adv_participation"],
            max_days_to_liquidate=b_data["liquidity_constraint"]["max_days_to_liquidate"]
        )
        budget = RiskBudgetRecord(
            volatility_budget=b_data["volatility_budget"],
            drawdown_limit=b_data["drawdown_limit"],
            liquidity_constraint=liquidity
        )
        record = RiskAllocationRecord(
            allocation_id=row[0],
            thesis_id=row[1],
            state=row[2],
            risk_budget=budget
        )
        
        return AllocationMapper.to_domain(record)

    def exists(self, allocation_id: str) -> bool:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM risk_allocation WHERE allocation_id = %s", (allocation_id,))
                return cur.fetchone() is not None

    def delete(self, allocation_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM risk_allocation WHERE allocation_id = %s", (allocation_id,))
            conn.commit()
