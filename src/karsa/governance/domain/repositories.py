from abc import ABC, abstractmethod
from typing import List, Optional
from karsa.governance.domain.models import (
    CompliancePolicy, AuthorizationPolicy, ExceptionToken, 
    ExceptionRevocation, GovernanceDecisionRecord, RiskStateSnapshot, PolicyURN,
    GovernanceAuditChain, GovernanceBudgetCache
)

class CompliancePolicyRepository(ABC):
    @abstractmethod
    def save(self, policy: CompliancePolicy) -> None:
        pass

    @abstractmethod
    def find_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        pass

    @abstractmethod
    def find_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        pass

    @abstractmethod
    def find_latest_by_urn(self, urn: PolicyURN) -> Optional[CompliancePolicy]:
        pass

    @abstractmethod
    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[CompliancePolicy]:
        pass

# Compatibility alias for legacy tests
PolicyDefinitionRepository = CompliancePolicyRepository

class AuthorizationPolicyRepository(ABC):
    @abstractmethod
    def save(self, policy: AuthorizationPolicy) -> None:
        pass

    @abstractmethod
    def find_by_id(self, policy_id: str) -> Optional[AuthorizationPolicy]:
        pass

    @abstractmethod
    def find_by_urn(self, urn_str: str) -> Optional[AuthorizationPolicy]:
        pass

    @abstractmethod
    def find_active_policy(self) -> Optional[AuthorizationPolicy]:
        pass

class ExceptionTokenRepository(ABC):
    @abstractmethod
    def save(self, token: ExceptionToken) -> None:
        pass

    @abstractmethod
    def find_by_hash(self, token_hash: str) -> Optional[ExceptionToken]:
        pass

    @abstractmethod
    def find_active_by_order_id(self, order_id: str) -> Optional[ExceptionToken]:
        pass

class ExceptionRevocationRepository(ABC):
    @abstractmethod
    def save(self, revocation: ExceptionRevocation) -> None:
        pass

    @abstractmethod
    def find_by_token_hash(self, token_hash: str) -> Optional[ExceptionRevocation]:
        pass

class GovernanceDecisionRecordRepository(ABC):
    @abstractmethod
    def save(self, record: GovernanceDecisionRecord) -> None:
        pass

    @abstractmethod
    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecisionRecord]:
        pass

# Compatibility alias for legacy tests
GovernanceDecisionRepository = GovernanceDecisionRecordRepository

class RiskStateSnapshotRepository(ABC):
    @abstractmethod
    def save(self, snapshot: RiskStateSnapshot) -> None:
        pass

    @abstractmethod
    def find_by_snapshot_id(self, portfolio_snapshot_id: str) -> Optional[RiskStateSnapshot]:
        pass

# Compatibility repositories for legacy tests
class GovernanceAuditRepository(ABC):
    @abstractmethod
    def append_chain(self, entry: GovernanceAuditChain) -> None:
        pass

    @abstractmethod
    def get_latest_entry(self) -> Optional[GovernanceAuditChain]:
        pass

class GovernanceBudgetCacheRepository(ABC):
    @abstractmethod
    def save(self, cache: GovernanceBudgetCache) -> None:
        pass

    @abstractmethod
    def find_by_workflow_id(self, workflow_id: str) -> Optional[GovernanceBudgetCache]:
        pass
