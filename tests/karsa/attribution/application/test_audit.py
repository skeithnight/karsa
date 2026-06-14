from karsa.attribution.application.commands import (
    ProcessRealizedOutcomeCommand,
    ApplyAttributionRestatementCommand
)
from karsa.attribution.domain.model.value_objects import GovernanceAuditContext

def test_governance_audit_context_creation():
    audit_ctx = GovernanceAuditContext(
        approval_reference="ref-999",
        approval_timestamp="2026-06-14T07:13:57Z",
        approved_by="governance-board",
        approval_reason="annual audit check"
    )
    assert audit_ctx.approval_reference == "ref-999"
    assert audit_ctx.approved_by == "governance-board"

def test_commands_creation():
    cmd1 = ProcessRealizedOutcomeCommand(
        outcome_id="out-1",
        sequence_id=42,
        source_context_id="ctx-1",
        gross_pnl=150.75,
        currency="USD"
    )
    assert cmd1.outcome_id == "out-1"
    assert cmd1.sequence_id == 42
    assert cmd1.gross_pnl == 150.75

    audit_ctx = GovernanceAuditContext(
        approval_reference="ref-999",
        approval_timestamp="2026-06-14T07:13:57Z",
        approved_by="governance-board",
        approval_reason="restatement audit"
    )
    cmd2 = ApplyAttributionRestatementCommand(
        outcome_id="out-1",
        sequence_id=42,
        gross_pnl=160.00,
        currency="USD",
        source_context_id="ctx-1",
        governance_audit_context=audit_ctx
    )
    assert cmd2.gross_pnl == 160.00
    assert cmd2.governance_audit_context.approval_reason == "restatement audit"

