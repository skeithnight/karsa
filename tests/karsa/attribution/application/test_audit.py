import pytest
from unittest.mock import MagicMock
from karsa.attribution.application.service import AttributionApplicationService
from karsa.attribution.application.commands import ApplyAttributionRestatementCommand, ProcessRealizedOutcomeCommand
from karsa.attribution.domain.model.value_objects import GovernanceAuditContext, OutcomeSequenceIdentity, PolicyInputSnapshot
from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.infrastructure.storage.lineage_repository import PostgresLineageRepository
from karsa.attribution.domain.service.attribution_service import AttributionService
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
import psycopg2

class MockUoW:
    def __init__(self):
        self.attribution_lineage_repository = MagicMock()
        self.attribution_projection_store = MagicMock()
        self.outbox_repository = MagicMock()
        self.connection = MagicMock()
        self.committed = False
        self.rolled_back = False

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True

def test_occ_conflict():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.rowcount = 0  # Simulate OCC failure

    repo = PostgresLineageRepository(conn)
    lin = AttributionLineage(OutcomeSequenceIdentity("o1", 1), "attr1", 1, version=2)
    
    with pytest.raises(ConcurrencyConflictError):
        repo.save(lin)

def test_duplicate_approval_is_noop():
    uow = MockUoW()
    cur = MagicMock()
    uow.connection.cursor.return_value = cur
    # Simulate IntegrityError on duplicate approval_reference
    cur.execute.side_effect = psycopg2.IntegrityError("Duplicate key")
    
    svc = AttributionApplicationService(uow)
    cmd = ApplyAttributionRestatementCommand("o1", 1, 100.0, "USD", "ctx1", GovernanceAuditContext("ref1", "now", "user", "reason"))
    
    # Should swallow exception and not commit or save outbox
    svc.apply_approved_restatement(cmd)
    
    assert uow.rolled_back == True
    assert uow.committed == False
    assert uow.outbox_repository.save.call_count == 0

def test_replay_from_policy_snapshot():
    # Mathematical Authority dictates execution
    historical_policy = PolicyInputSnapshot(
        "v1", "ROLE_WEIGHTED", "REBASE", "BANKERS", "LEXI", 
        {"AUTHOR": 0.9, "APPROVER": 0.1}, 2
    )
    contributors = [{"target_id": "t1", "role": "AUTHOR"}, {"target_id": "t2", "role": "APPROVER"}]
    
    allocations = AttributionService.calculate_allocations(100.0, "USD", contributors, historical_policy)
    
    assert allocations[0].target_identity == "t1"
    assert allocations[0].attributed_pnl == 90.0
    assert allocations[1].target_identity == "t2"
    assert allocations[1].attributed_pnl == 10.0

def test_projection_store_roundtrip():
    from karsa.attribution.infrastructure.storage.projection_store import PostgresProjectionStore
    import json
    
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    
    store = PostgresProjectionStore(conn)
    store.upsert("ctx1", [{"id": "t1"}])
    
    cur.execute.assert_called_with(
        "INSERT INTO attribution_input_projection (source_context_id, contributors) VALUES (%s, %s) ON CONFLICT (source_context_id) DO UPDATE SET contributors=EXCLUDED.contributors",
        ("ctx1", json.dumps([{"id": "t1"}]))
    )

def test_outbox_written_in_same_uow():
    uow = MockUoW()
    uow.attribution_lineage_repository.get_by_id.return_value = None # No existing
    uow.attribution_projection_store.get_by_id.return_value = [{"target_id": "t1", "role": "AUTHOR"}]
    
    svc = AttributionApplicationService(uow)
    cmd = ProcessRealizedOutcomeCommand("o1", 1, "ctx1", 100.0, "USD")
    
    svc.process_outcome(cmd)
    
    # Assert uow methods were called correctly within transaction
    uow.attribution_lineage_repository.save.assert_called_once()
    uow.outbox_repository.save.assert_called_once()
    assert uow.committed == True

