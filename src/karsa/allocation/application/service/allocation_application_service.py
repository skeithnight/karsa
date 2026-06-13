from typing import Optional
from karsa.allocation.domain.repository.allocation_repository import AllocationRepository
from karsa.allocation.application.port.memory_platform_port import MemoryPlatformPort, AllocationArtifactPayload
from karsa.allocation.domain.model.allocation import RiskAllocation, RiskBudget, LiquidityConstraint

class AllocationApplicationService:
    def __init__(self, repository: AllocationRepository, memory_port: MemoryPlatformPort):
        self.repository = repository
        self.memory_port = memory_port

    def _publish(self, allocation: RiskAllocation, event_type: str, details: dict = None) -> None:
        if details is None:
            details = {}
        payload = AllocationArtifactPayload(
            allocation_id=allocation.allocation_id,
            thesis_id=allocation.thesis_id,
            state=allocation.state.value,
            event_type=event_type,
            details=details
        )
        self.memory_port.publish_artifact(payload)

    def create_allocation(self, allocation_id: str, thesis_id: str, volatility_budget: float, drawdown_limit: float, max_adv_participation: float, max_days_to_liquidate: float) -> None:
        liquidity = LiquidityConstraint(
            max_adv_participation=max_adv_participation,
            max_days_to_liquidate=max_days_to_liquidate
        )
        budget = RiskBudget(
            volatility_budget=volatility_budget,
            drawdown_limit=drawdown_limit,
            liquidity_constraint=liquidity
        )
        allocation = RiskAllocation(allocation_id=allocation_id, thesis_id=thesis_id, risk_budget=budget)
        
        self.repository.save(allocation)
        
        self._publish(
            allocation, 
            event_type="ALLOCATION_CREATED",
            details={
                "volatility_budget": volatility_budget,
                "drawdown_limit": drawdown_limit
            }
        )

    def activate_allocation(self, allocation_id: str) -> None:
        allocation = self.repository.get_by_id(allocation_id)
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
            
        allocation.activate()
        self.repository.save(allocation)
        
        self._publish(allocation, event_type="ALLOCATION_ACTIVATED")

    def suspend_allocation(self, allocation_id: str) -> None:
        allocation = self.repository.get_by_id(allocation_id)
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
            
        allocation.suspend()
        self.repository.save(allocation)
        
        self._publish(allocation, event_type="ALLOCATION_SUSPENDED")

    def terminate_allocation(self, allocation_id: str) -> None:
        allocation = self.repository.get_by_id(allocation_id)
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
            
        allocation.terminate()
        self.repository.save(allocation)
        
        self._publish(allocation, event_type="ALLOCATION_TERMINATED")

    def scale_allocation_budget(self, allocation_id: str, realized_volatility: float) -> None:
        allocation = self.repository.get_by_id(allocation_id)
        if not allocation:
            raise ValueError(f"Allocation {allocation_id} not found")
            
        old_budget = allocation.risk_budget.volatility_budget
        allocation.scale_volatility_budget(realized_volatility)
        new_budget = allocation.risk_budget.volatility_budget
        
        self.repository.save(allocation)
        
        self._publish(
            allocation, 
            event_type="ALLOCATION_SCALED",
            details={
                "realized_volatility": realized_volatility,
                "old_volatility_budget": old_budget,
                "new_volatility_budget": new_budget
            }
        )
