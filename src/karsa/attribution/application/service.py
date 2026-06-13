import uuid
import datetime
import psycopg2
from typing import Any
from karsa.attribution.application.commands import ProcessRealizedOutcomeCommand, ApplyAttributionRestatementCommand
from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity
from karsa.attribution.domain.service.attribution_service import AttributionService
from karsa.attribution.domain.registry.policy_registry import AttributionPolicyRegistry
from karsa.attribution.events.attribution_events import AttributionCalculatedPayload, AttributionReversedPayload
from karsa.shared.events.envelope import PlatformEventEnvelope

class AttributionApplicationService:
    def __init__(self, uow):
        self.uow = uow

    def process_outcome(self, cmd: ProcessRealizedOutcomeCommand):
        with self.uow:
            identity = OutcomeSequenceIdentity(cmd.outcome_id, cmd.sequence_id)
            existing = self.uow.attribution_lineage_repository.get_by_id(identity)
            if existing: return # Idempotent handling of existing Gen 1
            
            contributors = self.uow.attribution_projection_store.get_by_id(cmd.source_context_id)
            policy = AttributionPolicyRegistry.get_policy("v1")
            
            allocations = AttributionService.calculate_allocations(cmd.gross_pnl, cmd.currency, contributors, policy)
            
            attr_id = str(uuid.uuid4())
            lineage = AttributionLineage(identity, attr_id, 1)
            self.uow.attribution_lineage_repository.save(lineage)
            
            payload = AttributionCalculatedPayload(
                attribution_id=attr_id,
                outcome_id=cmd.outcome_id,
                source_context_id=cmd.source_context_id,
                attribution_generation=1,
                outcome_sequence=cmd.sequence_id,
                policy_input_snapshot=policy.__dict__,
                allocations=[a.__dict__ for a in allocations]
            )
            
            env = PlatformEventEnvelope(
                event_id=str(uuid.uuid4()),
                event_type="AttributionCalculatedEvent",
                aggregate_type="Attribution",
                aggregate_id=attr_id,
                aggregate_version=1,
                schema_version="1.0",
                occurred_at=datetime.datetime.utcnow().isoformat(),
                payload=payload.__dict__,
                correlation_id=str(uuid.uuid4()),
                causation_id=str(uuid.uuid4())
            )
            self.uow.outbox_repository.save(env)
            self.uow.commit()

    def apply_approved_restatement(self, cmd: ApplyAttributionRestatementCommand):
        with self.uow:
            cur = self.uow.connection.cursor()
            try:
                cur.execute("INSERT INTO attribution_lineage_restatement (outcome_id, sequence_id, approval_reference, generation, created_at) VALUES (%s, %s, %s, %s, %s)",
                           (cmd.outcome_id, cmd.sequence_id, cmd.governance_audit_context.approval_reference, 0, datetime.datetime.utcnow()))
            except psycopg2.IntegrityError:
                self.uow.rollback()
                return # Duplicate approval reference, no-op
                
            identity = OutcomeSequenceIdentity(cmd.outcome_id, cmd.sequence_id)
            lineage = self.uow.attribution_lineage_repository.get_by_id(identity)
            if not lineage: raise Exception("Cannot restate missing outcome")
            
            parent_id = lineage.active_attribution_id
            new_attr_id = str(uuid.uuid4())
            lineage.advance_generation(new_attr_id)
            self.uow.attribution_lineage_repository.save(lineage)
            
            contributors = self.uow.attribution_projection_store.get_by_id(cmd.source_context_id)
            policy = AttributionPolicyRegistry.get_policy("v1")
            allocations = AttributionService.calculate_allocations(cmd.gross_pnl, cmd.currency, contributors, policy)
            
            rev_payload = AttributionReversedPayload(parent_id, cmd.governance_audit_context.__dict__, "Restatement Approved")
            env_rev = PlatformEventEnvelope(str(uuid.uuid4()), "AttributionReversedEvent", "Attribution", parent_id, lineage.aggregate_version, "1.0", datetime.datetime.utcnow().isoformat(), rev_payload.__dict__, str(uuid.uuid4()), str(uuid.uuid4()))
            self.uow.outbox_repository.save(env_rev)
            
            calc_payload = AttributionCalculatedPayload(
                attribution_id=new_attr_id,
                outcome_id=cmd.outcome_id,
                source_context_id=cmd.source_context_id,
                attribution_generation=lineage.current_generation,
                outcome_sequence=cmd.sequence_id,
                policy_input_snapshot=policy.__dict__,
                allocations=[a.__dict__ for a in allocations],
                governance_audit_context=cmd.governance_audit_context.__dict__,
                parent_attribution_id=parent_id
            )
            env_calc = PlatformEventEnvelope(str(uuid.uuid4()), "AttributionCalculatedEvent", "Attribution", new_attr_id, lineage.aggregate_version, "1.0", datetime.datetime.utcnow().isoformat(), calc_payload.__dict__, str(uuid.uuid4()), str(uuid.uuid4()))
            self.uow.outbox_repository.save(env_calc)
            
            self.uow.commit()
