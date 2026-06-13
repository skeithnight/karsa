import os
from pathlib import Path

base_dir = Path("src/karsa/attribution")
test_dir = Path("tests/karsa/attribution")

dirs = [
    base_dir / "domain" / "model",
    base_dir / "domain" / "service",
    base_dir / "domain" / "registry",
    base_dir / "application",
    base_dir / "events",
    base_dir / "infrastructure" / "storage",
    test_dir / "application",
    test_dir / "domain",
    test_dir / "infrastructure"
]

for d in dirs:
    d.mkdir(parents=True, exist_ok=True)
    (d / "__init__.py").touch()

with open(base_dir / "__init__.py", "w") as f:
    pass

with open(base_dir / "domain" / "model" / "value_objects.py", "w") as f:
    f.write('''from dataclasses import dataclass
from typing import Dict, Optional, List

@dataclass(frozen=True)
class OutcomeSequenceIdentity:
    outcome_id: str
    sequence_id: int

@dataclass(frozen=True)
class AttributionIdentity:
    attribution_id: str
    outcome_id: str
    source_context_id: str
    attribution_generation: int
    outcome_sequence: int
    parent_attribution_id: Optional[str] = None

@dataclass(frozen=True)
class ContributionWeight:
    role_identifier: str
    target_identity: str
    weight_fraction: float

@dataclass(frozen=True)
class PolicyInputSnapshot:
    policy_version: str
    weight_model: str
    normalization_strategy: str
    rounding_strategy: str
    allocation_ordering: str
    role_weights: Dict[str, float]
    currency_precision: int

@dataclass(frozen=True)
class GovernanceAuditContext:
    approval_reference: str
    approval_timestamp: str
    approved_by: str
    approval_reason: str

@dataclass(frozen=True)
class AttributedValue:
    target_identity: str
    gross_pnl: float
    attributed_pnl: float
    attribution_percentage: float
    currency: str
''')

with open(base_dir / "domain" / "model" / "lineage.py", "w") as f:
    f.write('''from typing import Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity

class AttributionLineage(VersionedAggregate):
    def __init__(self, identity: OutcomeSequenceIdentity, active_attribution_id: str, current_generation: int, version: int = 1):
        super().__init__()
        self.identity = identity
        self.active_attribution_id = active_attribution_id
        self.current_generation = current_generation
        self._aggregate_version = version

    def advance_generation(self, new_attribution_id: str):
        self.current_generation += 1
        self.active_attribution_id = new_attribution_id
        self.increment_version()
''')

with open(base_dir / "domain" / "service" / "attribution_service.py", "w") as f:
    f.write('''from typing import List, Dict, Any
from karsa.attribution.domain.model.value_objects import PolicyInputSnapshot, AttributedValue

class AttributionService:
    @staticmethod
    def calculate_allocations(gross_pnl: float, currency: str, contributors: List[Dict[str, Any]], policy: PolicyInputSnapshot) -> List[AttributedValue]:
        allocations = []
        # Normalization and weighting logic based on role_weights
        targets = sorted(contributors, key=lambda x: x['target_id']) # LEXICOGRAPHICAL_TARGET_ID
        
        total_weight = 0.0
        weights = []
        for c in targets:
            role = c.get('role', 'AUTHOR')
            w = policy.role_weights.get(role, 0.0)
            total_weight += w
            weights.append(w)
            
        remaining_pnl = gross_pnl
        for i, c in enumerate(targets):
            frac = weights[i] / total_weight if total_weight > 0 else 0.0
            
            if i == len(targets) - 1:
                # Give remainder to the last person lexicographically, or first?
                # Actually, LEXICOGRAPHICAL_TARGET_ID means remainder handled deterministically.
                val = remaining_pnl
            else:
                val = round(gross_pnl * frac, policy.currency_precision)
                remaining_pnl -= val
                
            allocations.append(AttributedValue(
                target_identity=c['target_id'],
                gross_pnl=gross_pnl,
                attributed_pnl=val,
                attribution_percentage=frac,
                currency=currency
            ))
        return allocations
''')

with open(base_dir / "domain" / "registry" / "policy_registry.py", "w") as f:
    f.write('''from karsa.attribution.domain.model.value_objects import PolicyInputSnapshot

class AttributionPolicyRegistry:
    @staticmethod
    def get_policy(version: str) -> PolicyInputSnapshot:
        return PolicyInputSnapshot(
            policy_version="v1",
            weight_model="ROLE_WEIGHTED",
            normalization_strategy="REBASE_TO_ONE",
            rounding_strategy="BANKERS_ROUNDING",
            allocation_ordering="LEXICOGRAPHICAL_TARGET_ID",
            role_weights={"AUTHOR": 0.6, "REFINER": 0.2, "APPROVER": 0.2},
            currency_precision=2
        )
''')

with open(base_dir / "events" / "attribution_events.py", "w") as f:
    f.write('''from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import datetime

@dataclass(frozen=True)
class AttributionCalculatedPayload:
    attribution_id: str
    outcome_id: str
    source_context_id: str
    attribution_generation: int
    outcome_sequence: int
    policy_input_snapshot: Dict[str, Any]
    allocations: List[Dict[str, Any]]
    governance_audit_context: Optional[Dict[str, str]] = None
    parent_attribution_id: Optional[str] = None
    attribution_scope: str = "REALIZED_PNL"
    algorithm_hash: str = "hash_v1"
    
@dataclass(frozen=True)
class AttributionReversedPayload:
    attribution_id: str
    governance_audit_context: Dict[str, str]
    reason: str
''')

with open(base_dir / "infrastructure" / "storage" / "lineage_repository.py", "w") as f:
    f.write('''from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity
from karsa.shared.infrastructure.uow.exceptions import ConcurrencyConflictError
from typing import Optional

class PostgresLineageRepository:
    def __init__(self, connection):
        self.conn = connection

    def get_by_id(self, identity: OutcomeSequenceIdentity) -> Optional[AttributionLineage]:
        cur = self.conn.cursor()
        cur.execute("SELECT active_attribution_id, current_generation, version FROM attribution_lineage WHERE outcome_id=%s AND sequence_id=%s", 
                   (identity.outcome_id, identity.sequence_id))
        row = cur.fetchone()
        if not row: return None
        return AttributionLineage(identity, row[0], row[1], row[2])

    def save(self, lineage: AttributionLineage):
        cur = self.conn.cursor()
        if lineage.aggregate_version == 1:
            cur.execute("INSERT INTO attribution_lineage (outcome_id, sequence_id, active_attribution_id, current_generation, version) VALUES (%s, %s, %s, %s, %s)",
                       (lineage.identity.outcome_id, lineage.identity.sequence_id, lineage.active_attribution_id, lineage.current_generation, lineage.aggregate_version))
        else:
            cur.execute("UPDATE attribution_lineage SET active_attribution_id=%s, current_generation=%s, version=%s WHERE outcome_id=%s AND sequence_id=%s AND version=%s",
                       (lineage.active_attribution_id, lineage.current_generation, lineage.aggregate_version, lineage.identity.outcome_id, lineage.identity.sequence_id, lineage.aggregate_version - 1))
            if cur.rowcount == 0:
                raise ConcurrencyConflictError(f"Concurrency conflict on lineage {lineage.identity}")
''')

with open(base_dir / "infrastructure" / "storage" / "projection_store.py", "w") as f:
    f.write('''import json
from typing import List, Dict, Any

class PostgresProjectionStore:
    def __init__(self, connection):
        self.conn = connection

    def upsert(self, source_context_id: str, contributors: List[Dict[str, Any]]):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO attribution_input_projection (source_context_id, contributors) VALUES (%s, %s) ON CONFLICT (source_context_id) DO UPDATE SET contributors=EXCLUDED.contributors",
                   (source_context_id, json.dumps(contributors)))

    def get_by_id(self, source_context_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT contributors FROM attribution_input_projection WHERE source_context_id=%s", (source_context_id,))
        row = cur.fetchone()
        return row[0] if row else []
''')

with open(base_dir / "application" / "commands.py", "w") as f:
    f.write('''from dataclasses import dataclass
from typing import Optional
from karsa.attribution.domain.model.value_objects import GovernanceAuditContext

@dataclass
class ProcessRealizedOutcomeCommand:
    outcome_id: str
    sequence_id: int
    source_context_id: str
    gross_pnl: float
    currency: str

@dataclass
class ApplyAttributionRestatementCommand:
    outcome_id: str
    sequence_id: int
    gross_pnl: float
    currency: str
    source_context_id: str
    governance_audit_context: GovernanceAuditContext
''')

with open(base_dir / "application" / "service.py", "w") as f:
    f.write('''import uuid
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
                payload=payload.__dict__
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
            env_rev = PlatformEventEnvelope(str(uuid.uuid4()), "AttributionReversedEvent", "Attribution", parent_id, lineage.aggregate_version, "1.0", datetime.datetime.utcnow().isoformat(), rev_payload.__dict__)
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
            env_calc = PlatformEventEnvelope(str(uuid.uuid4()), "AttributionCalculatedEvent", "Attribution", new_attr_id, lineage.aggregate_version, "1.0", datetime.datetime.utcnow().isoformat(), calc_payload.__dict__)
            self.uow.outbox_repository.save(env_calc)
            
            self.uow.commit()
''')

with open(base_dir / "infrastructure" / "storage" / "migration_v1.sql", "w") as f:
    f.write('''
CREATE TABLE attribution_lineage (
    outcome_id VARCHAR NOT NULL,
    sequence_id INT NOT NULL,
    active_attribution_id VARCHAR NOT NULL,
    current_generation INT NOT NULL,
    version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (outcome_id, sequence_id)
);

CREATE TABLE attribution_lineage_restatement (
    outcome_id VARCHAR NOT NULL,
    sequence_id INT NOT NULL,
    approval_reference VARCHAR NOT NULL,
    generation INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (outcome_id, sequence_id, approval_reference)
);

CREATE TABLE attribution_input_projection (
    source_context_id VARCHAR PRIMARY KEY,
    contributors JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

with open(test_dir / "domain" / "test_attribution_service.py", "w") as f:
    f.write('''from karsa.attribution.domain.service.attribution_service import AttributionService
from karsa.attribution.domain.model.value_objects import PolicyInputSnapshot

def test_attribution_split_math():
    policy = PolicyInputSnapshot("v1", "ROLE_WEIGHTED", "REBASE", "BANKERS", "LEXI", {"AUTHOR": 0.6, "REFINER": 0.4}, 2)
    contributors = [{"target_id": "user1", "role": "AUTHOR"}, {"target_id": "user2", "role": "REFINER"}]
    
    allocations = AttributionService.calculate_allocations(100.0, "USD", contributors, policy)
    
    assert allocations[0].target_identity == "user1"
    assert allocations[0].attributed_pnl == 60.0
    assert allocations[1].target_identity == "user2"
    assert allocations[1].attributed_pnl == 40.0
''')

with open(test_dir / "domain" / "test_lineage.py", "w") as f:
    f.write('''from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity

def test_lineage_advance_generation():
    identity = OutcomeSequenceIdentity("out_1", 1)
    lin = AttributionLineage(identity, "attr_1", 1)
    
    lin.advance_generation("attr_2")
    
    assert lin.current_generation == 2
    assert lin.active_attribution_id == "attr_2"
    assert lin.aggregate_version == 2
''')

