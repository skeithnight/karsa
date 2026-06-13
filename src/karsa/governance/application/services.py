import os
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from karsa.governance.domain.repositories import (
    PolicyDefinitionRepository, GovernanceDecisionRepository, 
    GovernanceAuditRepository, GovernanceBudgetCacheRepository
)
from karsa.governance.domain.models import (
    PolicyDefinition, PolicyURN, PolicyScope, PolicyCondition, PolicyAction,
    PolicyRule, GovernanceDecision, GovernanceAuditChain, GovernanceBudgetCache,
    PolicyLifecycleState
)
from karsa.governance.domain.events import (
    PolicyCreatedEvent, PolicyActivatedEvent, PolicySuspendedEvent, PolicyRevokedEvent,
    GovernanceDecisionCreatedEvent, CapabilityExecutionApprovedEvent, CapabilityExecutionDeniedEvent
)

class PolicyRegistryService:
    def __init__(
        self,
        policy_repo: PolicyDefinitionRepository,
        event_publisher: Optional[Callable[[Any], None]] = None
    ):
        self.policy_repo = policy_repo
        self.event_publisher = event_publisher

    def register_policy(
        self,
        policy_id: str,
        urn_str: str,
        priority: int,
        scope: PolicyScope,
        rules: List[PolicyRule]
    ) -> PolicyDefinition:
        urn = PolicyURN.from_string(urn_str)

        if self.policy_repo.find_by_id(policy_id):
            raise ValueError(f"Policy with ID {policy_id} already exists.")
        if self.policy_repo.find_by_urn(urn):
            raise ValueError(f"Policy URN {urn_str} already exists.")

        policy = PolicyDefinition(
            policy_id=policy_id,
            policy_urn=urn,
            priority=priority,
            scope=scope,
            rules=rules
        )
        self.policy_repo.save(policy)

        if self.event_publisher:
            self.event_publisher(PolicyCreatedEvent(
                policy_id=policy.policy_id,
                policy_urn_str=policy.policy_urn.to_string(),
                target_type=scope.target_type,
                target_urn=scope.target_urn,
                timestamp=datetime.now(timezone.utc)
            ))

        return policy

    def transition_policy_state(
        self,
        policy_id: str,
        new_state: PolicyLifecycleState,
        reason: str = ""
    ) -> None:
        policy = self.policy_repo.find_by_id(policy_id)
        if not policy:
            raise ValueError(f"Policy with ID {policy_id} not found.")

        policy.transition_to(new_state, reason)
        self.policy_repo.save(policy)

        if self.event_publisher:
            timestamp = datetime.now(timezone.utc)
            if new_state == PolicyLifecycleState.ACTIVE:
                self.event_publisher(PolicyActivatedEvent(policy_id=policy_id, reason=reason, timestamp=timestamp))
            elif new_state == PolicyLifecycleState.SUSPENDED:
                self.event_publisher(PolicySuspendedEvent(policy_id=policy_id, reason=reason, timestamp=timestamp))
            elif new_state == PolicyLifecycleState.REVOKED:
                self.event_publisher(PolicyRevokedEvent(policy_id=policy_id, reason=reason, timestamp=timestamp))


class GovernanceAuditService:
    def __init__(self, audit_repo: GovernanceAuditRepository):
        self.audit_repo = audit_repo
        self._lock = threading.Lock()

    def process_decision(self, decision_id: str, outcome: str) -> None:
        # Sequential processing block using Lock to prevent concurrent append race conditions
        with self._lock:
            latest = self.audit_repo.get_latest_entry()
            previous_hash = latest.current_hash if latest else ""
            current_hash = GovernanceAuditChain.calculate_hash(decision_id, outcome, previous_hash)

            entry = GovernanceAuditChain(
                decision_id=decision_id,
                previous_hash=previous_hash,
                current_hash=current_hash
            )
            self.audit_repo.append_chain(entry)


class PolicyEvaluationService:
    def __init__(
        self,
        policy_repo: PolicyDefinitionRepository,
        budget_cache_repo: GovernanceBudgetCacheRepository,
        audit_service: Optional[GovernanceAuditService] = None,
        event_publisher: Optional[Callable[[Any], None]] = None,
        bypass_log_path: str = ".karsa/governance/bypass_audit.log"
    ):
        self.policy_repo = policy_repo
        self.budget_cache_repo = budget_cache_repo
        self.audit_service = audit_service
        self.event_publisher = event_publisher
        self.bypass_log_path = bypass_log_path

    def _validate_override_token(self, token: str) -> bool:
        return token.startswith("admin-override-token-")

    def check_execution_authorization(
        self,
        execution_id: str,
        capability_urn: str,
        context: Dict[str, Any],
        replay_mode: bool = False,
        historical_decision: Optional[GovernanceDecision] = None,
        override_token: Optional[str] = None
    ) -> GovernanceDecision:
        # 1. Replay Determinism Bypass
        if replay_mode:
            if not historical_decision:
                raise ValueError("historical_decision must be provided in replay mode.")
            return historical_decision

        # 2. Emergency Override Mode
        if override_token:
            if self._validate_override_token(override_token):
                # Write override record directly to local append-only security log file
                os.makedirs(os.path.dirname(self.bypass_log_path), exist_ok=True)
                timestamp = datetime.now(timezone.utc).isoformat()
                log_entry = f"[{timestamp}] OVERRIDE: exec_id={execution_id}, token={override_token}\n"
                with open(self.bypass_log_path, "a") as f:
                    f.write(log_entry)

                decision = GovernanceDecision(
                    execution_id=execution_id,
                    outcome="APPROVED",
                    reason="EMERGENCY_OVERRIDE_GRANTED",
                    estimated_cost=0.0
                )
                return decision
            else:
                raise ValueError("Invalid emergency override token.")

        # 3. Normal Path
        # Retrieve active policies scoped to CAPABILITY or WORKFLOW
        policies = self.policy_repo.find_active_for_scope("CAPABILITY", capability_urn)
        if "workflow_id" in context:
            policies.extend(self.policy_repo.find_active_for_scope("WORKFLOW", context["workflow_id"]))

        # Deny-by-default if no active policies match the scope
        if not policies:
            decision = GovernanceDecision(
                execution_id=execution_id,
                outcome="DENIED",
                reason="DENY_BY_DEFAULT: No active policies apply to this execution context.",
                estimated_cost=context.get("estimated_cost", 0.0)
            )
            if self.event_publisher:
                self.event_publisher(GovernanceDecisionCreatedEvent(
                    decision_id=decision.decision_id,
                    execution_id=execution_id,
                    outcome=decision.outcome,
                    reason=decision.reason,
                    estimated_cost=decision.estimated_cost,
                    timestamp=datetime.now(timezone.utc)
                ))
                self.event_publisher(CapabilityExecutionDeniedEvent(
                    execution_id=execution_id,
                    capability_urn=capability_urn,
                    decision_id=decision.decision_id,
                    reason=decision.reason,
                    timestamp=datetime.now(timezone.utc)
                ))
            return decision

        decision_outcome = "APPROVED"
        denial_reason = ""

        # 4. Budget Governance Constraint Evaluation
        if "workflow_id" in context:
            workflow_id = context["workflow_id"]
            budget_cache = self.budget_cache_repo.find_by_workflow_id(workflow_id)
            if budget_cache:
                # Freshness verification
                if budget_cache.is_stale(max_stale_limit_seconds=60):
                    raise Exception("StaleBudgetSnapshotError: Budget cache snapshot is older than 60 seconds.")
                
                estimated_cost = context.get("estimated_cost", 0.0)
                if estimated_cost > budget_cache.remaining_budget:
                    decision_outcome = "DENIED"
                    denial_reason = f"BudgetExceeded: Estimated cost {estimated_cost} exceeds remaining budget {budget_cache.remaining_budget}."

        # 5. Evaluate Rules inside matching policies if not already denied by budget
        if decision_outcome != "DENIED":
            # Sort policies by priority ascending
            sorted_policies = sorted(policies, key=lambda p: p.priority)
            for p in sorted_policies:
                # Sort rules inside policy by priority ascending
                sorted_rules = sorted(p.rules, key=lambda r: r.priority)
                for r in sorted_rules:
                    if r.condition and r.condition.evaluate(context):
                        if r.action == PolicyAction.DENY:
                            decision_outcome = "DENIED"
                            denial_reason = f"PolicyDeny: Violates policy {p.policy_urn.to_string()} rule {r.rule_id}."
                            break
                if decision_outcome == "DENIED":
                    break

        decision = GovernanceDecision(
            execution_id=execution_id,
            outcome=decision_outcome,
            reason=denial_reason or "Authorization approved.",
            estimated_cost=context.get("estimated_cost", 0.0)
        )

        # 6. Local Event Dispatch Pattern
        if self.event_publisher:
            timestamp = datetime.now(timezone.utc)
            self.event_publisher(GovernanceDecisionCreatedEvent(
                decision_id=decision.decision_id,
                execution_id=execution_id,
                outcome=decision.outcome,
                reason=decision.reason,
                estimated_cost=decision.estimated_cost,
                timestamp=timestamp
            ))
            if decision.outcome == "APPROVED":
                self.event_publisher(CapabilityExecutionApprovedEvent(
                    execution_id=execution_id,
                    capability_urn=capability_urn,
                    decision_id=decision.decision_id,
                    timestamp=timestamp
                ))
            else:
                self.event_publisher(CapabilityExecutionDeniedEvent(
                    execution_id=execution_id,
                    capability_urn=capability_urn,
                    decision_id=decision.decision_id,
                    reason=decision.reason,
                    timestamp=timestamp
                ))

        # 7. Asynchronous Audit Chain updates (Layer B) via simple thread to decouple write execution latency
        if self.audit_service:
            thread = threading.Thread(
                target=self.audit_service.process_decision,
                args=(decision.decision_id, decision.outcome)
            )
            thread.start()

        return decision
