import uuid
from datetime import datetime, timezone
from karsa.bootstrap import ApplicationContainer
from karsa.domain.events import DomainEvent
from karsa.shared.infrastructure.event_journal import EventJournalRepository

class DecisionApprovedEvent(DomainEvent):
    def __init__(self, decision_id):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"CIODecision-{decision_id}"
        self.aggregate_id = decision_id
        self.aggregate_type = "CIODecision"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.decision_id = decision_id
    def to_dict(self):
        return {"decision_id": self.decision_id}

class ThesisActivatedEvent(DomainEvent):
    def __init__(self, thesis_urn):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Thesis-{thesis_urn}"
        self.aggregate_id = thesis_urn
        self.aggregate_type = "Thesis"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.thesis_urn = thesis_urn
    def to_dict(self):
        return {"thesis_urn": self.thesis_urn}

class DecisionLineageCreatedEvent(DomainEvent):
    def __init__(self, lineage_id, decision_id):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Lineage-{lineage_id}"
        self.aggregate_id = lineage_id
        self.aggregate_type = "Lineage"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.lineage_id = lineage_id
        self.decision_id = decision_id
        self.forecast_id = str(uuid.uuid4())
        self.correlation_id = lineage_id
        self.causation_id = decision_id
    def to_dict(self):
        return {"lineage_id": self.lineage_id, "decision_id": self.decision_id, "forecast_id": self.forecast_id}

class LineageNodeAddedEvent(DomainEvent):
    def __init__(self, lineage_id, worker_urn):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Lineage-{lineage_id}"
        self.aggregate_id = lineage_id
        self.aggregate_type = "Lineage"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.lineage_id = lineage_id
        self.node_id = str(uuid.uuid4())
        self.capability_id = str(uuid.uuid4())
        self.worker_urn = worker_urn
        self.role = "AUTHOR"
        self.correlation_id = lineage_id
        self.causation_id = lineage_id
    def to_dict(self):
        return {"lineage_id": self.lineage_id, "node_id": self.node_id, "capability_id": self.capability_id, "worker_urn": self.worker_urn, "role": self.role}

class AttributionFactGeneratedEvent(DomainEvent):
    def __init__(self, lineage_id):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Lineage-{lineage_id}"
        self.aggregate_id = lineage_id
        self.aggregate_type = "Lineage"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.lineage_id = lineage_id
        self.fact_id = str(uuid.uuid4())
        self.assessment_id = str(uuid.uuid4())
        self.dimensions = {"alpha": "0.05"}
        self.correlation_id = lineage_id
        self.causation_id = lineage_id
    def to_dict(self):
        return {"lineage_id": self.lineage_id, "fact_id": self.fact_id, "assessment_id": self.assessment_id, "dimensions": self.dimensions}

class AttributionAssessmentSealedEvent(DomainEvent):
    def __init__(self, lineage_id):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Lineage-{lineage_id}"
        self.aggregate_id = lineage_id
        self.aggregate_type = "Lineage"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.lineage_id = lineage_id
        self.assessment_id = str(uuid.uuid4())
        self.fact_ids_list = [str(uuid.uuid4())]
        self.fact_count = 1
        self.provenance_urn = "urn:provenance"
        self.correlation_id = lineage_id
        self.causation_id = lineage_id
    def to_dict(self):
        return {"lineage_id": self.lineage_id, "assessment_id": self.assessment_id, "fact_ids_list": self.fact_ids_list, "fact_count": self.fact_count, "provenance_urn": self.provenance_urn}

class WorkerAlphaRecordedEvent(DomainEvent):
    def __init__(self, worker_urn, alpha_delta, cumulative_alpha):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Worker-{worker_urn}"
        self.aggregate_id = worker_urn
        self.aggregate_type = "Worker"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.worker_urn = worker_urn
        self.alpha_delta = alpha_delta
        self.cumulative_alpha = cumulative_alpha
        self.subject_type = "ANALYST"
        self.regime_urn = "urn:karsa:regime:seed"
    def to_dict(self):
        return {"worker_urn": self.worker_urn, "alpha_delta": self.alpha_delta, "cumulative_alpha": self.cumulative_alpha, "subject_type": self.subject_type, "regime_urn": self.regime_urn}

class WorkerLifecycleTransitionedEvent(DomainEvent):
    def __init__(self, worker_urn, old_state, new_state):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Worker-{worker_urn}"
        self.aggregate_id = worker_urn
        self.aggregate_type = "Worker"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.worker_urn = worker_urn
        self.old_state = old_state
        self.new_state = new_state
        self.authority = "SYSTEM"
        self.reason = "Activation"
        self.subject_type = "ANALYST"
    def to_dict(self):
        return {"worker_urn": self.worker_urn, "old_state": self.old_state, "new_state": self.new_state, "authority": self.authority, "reason": self.reason, "subject_type": self.subject_type}

class CreditAllocatedEvent(DomainEvent):
    def __init__(self, subject_urn):
        super().__init__()
        self.event_id = str(uuid.uuid4())
        self.stream_id = f"Worker-{subject_urn}"
        self.aggregate_id = subject_urn
        self.aggregate_type = "Worker"
        self.occurred_at = datetime.now(timezone.utc)
        self.schema_version = 1
        self.subject_urn = subject_urn
        self.parent_node_id = "urn:karsa:worker:firm"
        self.attribution_urn = "urn:karsa:attribution:seed"
        self.skill_ratio = 0.8
    def to_dict(self):
        return {"subject_urn": self.subject_urn, "parent_node_id": self.parent_node_id, "attribution_urn": self.attribution_urn, "skill_ratio": self.skill_ratio}

def seed_intelligence_pipeline():
    container = ApplicationContainer()
    
    with container.pool.connection() as conn:
        repo = EventJournalRepository(conn)
        
        # Generate chain for analyst-6 (Projection Independence Test retry)
        analyst_id = "urn:karsa:worker:analyst-6"
        lineage_id = "lin-activation-6"
        decision_id = "dec-activation-6"
        forecast_id = str(uuid.uuid4())
        node_id = str(uuid.uuid4())
        cap_id = str(uuid.uuid4())
        alpha_val = 0.66
        i = 6
        
        events_to_append = [
            WorkerLifecycleTransitionedEvent(
                worker_urn=analyst_id,
                old_state="INACTIVE",
                new_state="ACTIVE"
            ),
            WorkerAlphaRecordedEvent(
                worker_urn=analyst_id,
                alpha_delta=alpha_val,
                cumulative_alpha=alpha_val
            ),
            DecisionLineageCreatedEvent(
                lineage_id=lineage_id,
                decision_id=decision_id
            ),
            LineageNodeAddedEvent(
                lineage_id=lineage_id,
                worker_urn=analyst_id
            ),
            AttributionFactGeneratedEvent(
                lineage_id=lineage_id
            ),
            AttributionAssessmentSealedEvent(
                lineage_id=lineage_id
            ),
            CreditAllocatedEvent(
                subject_urn=analyst_id
            )
        ]
        
        for event in events_to_append:
            event.stream_id = getattr(event, 'stream_id', analyst_id)
            if hasattr(event, 'dimensions'):
                event.dimensions = {"alpha": alpha_val}

        with conn.transaction():
            for event in events_to_append:
                event.event_id = str(uuid.uuid4())
                try:
                    current_ver = repo.get_current_stream_version(event.stream_id) or 0
                    repo.append(event, current_ver + 1)
                    print(f"Appended {event.__class__.__name__} to stream {event.stream_id} v{current_ver+1}")
                except Exception as e:
                    print(f"Error appending event: {e}")
                
    container.close()

if __name__ == "__main__":
    seed_intelligence_pipeline()
