from typing import Optional
from datetime import datetime
from karsa.domain.models import WorkflowSnapshot, GovernancePolicySnapshot, GovernanceDecision, ViolationContext

class GovernanceEvaluator:
    def __init__(self):
        pass

    def evaluate(self, snapshot: WorkflowSnapshot, execution_id: str, review_cycle_id: str) -> GovernanceDecision:
        policy = snapshot.policy
        if not policy:
            return GovernanceDecision(
                workflow_id=snapshot.workflow_id,
                review_cycle_id=review_cycle_id,
                execution_id=execution_id,
                sequence_number=snapshot.last_sequence_number + 1,
                decision_type="ALLOW",
                reason="No governance policy enforced."
            )
            
        metrics = snapshot.data.get("metrics", {})
        review_metrics = snapshot.data.get("review", {}).get("review_cycle_metrics", {})
        
        # 1. Workflow Cost
        total_cost = metrics.get("total_cost", 0.0)
        if policy.max_workflow_cost > 0 and total_cost >= policy.max_workflow_cost:
            return self._deny(snapshot, review_cycle_id, execution_id, "max_workflow_cost", policy.max_workflow_cost, total_cost)
            
        # 2. Workflow Tokens
        total_tokens = metrics.get("total_tokens", 0)
        if policy.max_workflow_tokens > 0 and total_tokens >= policy.max_workflow_tokens:
            return self._deny(snapshot, review_cycle_id, execution_id, "max_workflow_tokens", float(policy.max_workflow_tokens), float(total_tokens))
            
        # 3. Review Cycles
        execution_count = metrics.get("execution_count", 0)
        if policy.max_review_cycles > 0 and execution_count >= policy.max_review_cycles:
            return self._deny(snapshot, review_cycle_id, execution_id, "max_review_cycles", float(policy.max_review_cycles), float(execution_count))
            
        # 4. Cycle Cost
        cycle_cost = review_metrics.get("total_cost", 0.0)
        if policy.max_cycle_cost > 0 and cycle_cost >= policy.max_cycle_cost:
            return self._deny(snapshot, review_cycle_id, execution_id, "max_cycle_cost", policy.max_cycle_cost, cycle_cost)
            
        return GovernanceDecision(
            workflow_id=snapshot.workflow_id,
            review_cycle_id=review_cycle_id,
            execution_id=execution_id,
            sequence_number=snapshot.last_sequence_number + 1,
            decision_type="ALLOW",
            reason="All metrics within governance limits."
        )

    def _deny(self, snapshot: WorkflowSnapshot, review_cycle_id: str, execution_id: str, limit_name: str, limit_value: float, actual_value: float) -> GovernanceDecision:
        vc = ViolationContext(
            limit_name=limit_name,
            limit_value=limit_value,
            actual_value=actual_value
        )
        return GovernanceDecision(
            workflow_id=snapshot.workflow_id,
            review_cycle_id=review_cycle_id,
            execution_id=execution_id,
            sequence_number=snapshot.last_sequence_number + 1,
            decision_type="DENY",
            reason=f"Governance limit breached: {limit_name}",
            violation_context=vc
        )
