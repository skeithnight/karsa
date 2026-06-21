"""InvestmentWorkflowBootstrap -- Sprint-13. ADR-140.

Wires all investment workflow dependencies.
Composition root for the investment workflow bounded context.
"""

from dataclasses import dataclass

from karsa.investment_workflow.application.investment_decision_service import (
    InvestmentDecisionService,
)
from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_decision_repository import (
    InMemoryInvestmentDecisionRepository,
)
from karsa.investment_workflow.infrastructure.persistence.in_memory_investment_outbox_repository import (
    InMemoryInvestmentOutboxRepository,
)
from karsa.investment_workflow.integration.investment_workflow_command_facade import (
    InvestmentWorkflowCommandFacade,
)
from karsa.investment_workflow.integration.investment_workflow_query_facade import (
    InvestmentWorkflowQueryFacade,
)


@dataclass
class InvestmentWorkflowContainer:
    """Complete wiring of investment workflow components."""

    decision_repo: InMemoryInvestmentDecisionRepository
    outbox_repo: InMemoryInvestmentOutboxRepository
    decision_service: InvestmentDecisionService
    command_facade: InvestmentWorkflowCommandFacade
    query_facade: InvestmentWorkflowQueryFacade


def bootstrap() -> InvestmentWorkflowContainer:
    """Bootstrap all investment workflow components with in-memory repos."""
    decision_repo = InMemoryInvestmentDecisionRepository()
    outbox_repo = InMemoryInvestmentOutboxRepository()

    decision_service = InvestmentDecisionService(
        decision_repo=decision_repo,
        outbox_repo=outbox_repo,
    )

    command_facade = InvestmentWorkflowCommandFacade(
        decision_service=decision_service,
    )

    query_facade = InvestmentWorkflowQueryFacade(
        decision_repo=decision_repo,
    )

    return InvestmentWorkflowContainer(
        decision_repo=decision_repo,
        outbox_repo=outbox_repo,
        decision_service=decision_service,
        command_facade=command_facade,
        query_facade=query_facade,
    )
