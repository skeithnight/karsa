from abc import ABC, abstractmethod
from typing import List, Optional
from karsa.governance.domain.models import (
    PolicyDefinition, PolicyURN, GovernanceDecision, GovernanceAuditChain, GovernanceBudgetCache
)

class PolicyDefinitionRepository(ABC):
    @abstractmethod
    def save(self, policy: PolicyDefinition) -> None:
        pass

    @abstractmethod
    def find_by_id(self, policy_id: str) -> Optional[PolicyDefinition]:
        pass

    @abstractmethod
    def find_by_urn(self, urn: PolicyURN) -> Optional[PolicyDefinition]:
        pass

    @abstractmethod
    def find_active_for_scope(self, target_type: str, target_urn: str) -> List[PolicyDefinition]:
        pass

class GovernanceDecisionRepository(ABC):
    @abstractmethod
    def save(self, decision: GovernanceDecision) -> None:
        pass

    @abstractmethod
    def find_by_id(self, decision_id: str) -> Optional[GovernanceDecision]:
        pass

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
