from typing import Optional, Dict
from karsa.allocation.domain.repository.allocation_repository import AllocationRepository
from karsa.allocation.domain.model.allocation import RiskAllocation
from karsa.allocation.infrastructure.storage.allocation_mapper import AllocationMapper

class InMemoryAllocationRepository(AllocationRepository):
    def __init__(self):
        self.storage: Dict[str, dict] = {}

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
        
        record_dict = {
            "allocation_id": record.allocation_id,
            "thesis_id": record.thesis_id,
            "state": record.state,
            "risk_budget": budget_dict
        }
        
        self.storage[allocation.allocation_id] = record_dict

    def get_by_id(self, allocation_id: str) -> Optional[RiskAllocation]:
        record_dict = self.storage.get(allocation_id)
        if not record_dict:
            return None
            
        from karsa.allocation.infrastructure.storage.allocation_records import (
            RiskAllocationRecord, RiskBudgetRecord, LiquidityConstraintRecord
        )
        
        liquidity = LiquidityConstraintRecord(
            max_adv_participation=record_dict["risk_budget"]["liquidity_constraint"]["max_adv_participation"],
            max_days_to_liquidate=record_dict["risk_budget"]["liquidity_constraint"]["max_days_to_liquidate"]
        )
        
        budget = RiskBudgetRecord(
            volatility_budget=record_dict["risk_budget"]["volatility_budget"],
            drawdown_limit=record_dict["risk_budget"]["drawdown_limit"],
            liquidity_constraint=liquidity
        )
        
        record = RiskAllocationRecord(
            allocation_id=record_dict["allocation_id"],
            thesis_id=record_dict["thesis_id"],
            state=record_dict["state"],
            risk_budget=budget
        )
        
        return AllocationMapper.to_domain(record)

    def exists(self, allocation_id: str) -> bool:
        return allocation_id in self.storage

    def delete(self, allocation_id: str) -> None:
        self.storage.pop(allocation_id, None)
