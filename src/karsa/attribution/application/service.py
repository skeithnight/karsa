import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional

from karsa.attribution.domain.model.models import AttributionSession, PerformanceAttributionRecord
from karsa.attribution.domain.model.repositories import AttributionSessionRepository, PerformanceAttributionRepository
from karsa.attribution.domain.model.value_objects import (
    CanonicalManifestSerializer,
    FrongelloCompounding,
    CarinoCompounding,
    MencheroCompounding,
    CompoundingStrategy
)
from karsa.attribution.events.events import (
    AttributionCalculatedEvent,
    AttributionSupersededEvent,
    AttributionInvalidatedEvent,
    AttributionRecomputedEvent
)


class AttributionCalculationService:
    def __init__(
        self,
        session_repo: AttributionSessionRepository,
        record_repo: PerformanceAttributionRepository,
        events_list: Optional[List[Any]] = None
    ):
        self.session_repo = session_repo
        self.record_repo = record_repo
        self.events_list = events_list if events_list is not None else []

    def _get_strategy(self, name: str) -> CompoundingStrategy:
        if name == "FRONGELLO":
            return FrongelloCompounding()
        elif name == "CARINO":
            return CarinoCompounding()
        elif name == "MENCHERO":
            return MencheroCompounding()
        raise ValueError(f"Unknown strategy: {name}")

    def stage_session(
        self,
        session_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
        compounding_strategy: str = "FRONGELLO"
    ) -> AttributionSession:
        session = AttributionSession(
            session_id=session_id,
            horizon_start=horizon_start,
            horizon_end=horizon_end,
            state="STAGED",
            compounding_strategy=compounding_strategy
        )
        self.session_repo.save(session)
        return session

    def calculate_attribution(self, session_id: str, inputs: dict) -> List[PerformanceAttributionRecord]:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.transition_to("COMPUTING")
        self.session_repo.save(session)

        # Generate canonical hash of inputs and bind to session
        input_hash = CanonicalManifestSerializer.generate_hash(inputs)
        session.raw_input_manifest_hash = input_hash

        # Extract returns and effects
        daily_returns = inputs.get("daily_returns", [])
        daily_effects = inputs.get("daily_effects", {}) # map of asset_urn -> list of daily effects
        
        # Determine compounding strategy
        strategy = self._get_strategy(session.compounding_strategy)
        calculated_records = []

        # Iterate assets and calculate multi-period returns
        for asset_urn, effects_list in daily_effects.items():
            smoothed = strategy.compound_returns(daily_returns, effects_list)
            
            # Extract references from inputs or defaults
            decision_id = inputs.get("decision_id", f"urn:decision:{session_id}")
            thesis_urn = inputs.get("thesis_urn", "urn:thesis:default")
            worker_urn = inputs.get("worker_urn", "urn:worker:default")
            capability_urn = inputs.get("capability_urn", "urn:capability:default")
            regime_urn = inputs.get("regime_urn", "urn:regime:default")

            record = PerformanceAttributionRecord(
                record_id=str(uuid.uuid4()),
                session_id=session_id,
                decision_id=decision_id,
                thesis_urn=thesis_urn,
                worker_urn=worker_urn,
                capability_urn=capability_urn,
                regime_urn=regime_urn,
                asset_urn=asset_urn,
                selection_return=smoothed.get("selection", Decimal("0.0")),
                allocation_return=smoothed.get("allocation", Decimal("0.0")),
                execution_return=smoothed.get("execution", Decimal("0.0")),
                beta_return=smoothed.get("beta", Decimal("0.0")),
                liquidation_tracking_residual=smoothed.get("residual", Decimal("0.0")),
                attribution_version=1,
                is_active=True
            )
            self.record_repo.save(record)
            calculated_records.append(record)

        session.transition_to("CALIBRATED")
        self.session_repo.save(session)
        return calculated_records

    def seal_session(self, session_id: str) -> AttributionCalculatedEvent:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.transition_to("SEALED")
        self.session_repo.save(session)

        # Query all records
        records = self.record_repo.find_by_session(session_id)
        records_payload = [r.to_dict() for r in records]

        event = AttributionCalculatedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=session_id,
            causation_id=session_id,
            session_id=session_id,
            calculated_at=datetime.utcnow(),
            records=records_payload
        )
        self.events_list.append(event)
        return event


class AttributionRecomputationService:
    def __init__(
        self,
        session_repo: AttributionSessionRepository,
        record_repo: PerformanceAttributionRepository,
        idempotency_cache: Optional[Dict[str, bool]] = None,
        events_list: Optional[List[Any]] = None
    ):
        self.session_repo = session_repo
        self.record_repo = record_repo
        self.idempotency_cache = idempotency_cache if idempotency_cache is not None else {}
        self.events_list = events_list if events_list is not None else []

    def _get_strategy(self, name: str) -> CompoundingStrategy:
        if name == "FRONGELLO":
            return FrongelloCompounding()
        elif name == "CARINO":
            return CarinoCompounding()
        elif name == "MENCHERO":
            return MencheroCompounding()
        raise ValueError(f"Unknown strategy: {name}")

    def recompute_horizon(
        self,
        session_id: str,
        new_inputs: dict,
        recalculation_request_id: str
    ) -> List[PerformanceAttributionRecord]:
        # Idempotency Check
        if recalculation_request_id in self.idempotency_cache:
            # Drop recalculation request
            return []
        self.idempotency_cache[recalculation_request_id] = True

        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        new_hash = CanonicalManifestSerializer.generate_hash(new_inputs)
        
        # If input data is identical to current manifest, skip recomputation to protect resources
        if session.raw_input_manifest_hash == new_hash:
            return self.record_repo.find_by_session(session_id)

        # Retrieve previous records to find max version
        old_records = self.record_repo.find_by_session(session_id)
        max_ver = max((r.attribution_version for r in old_records), default=1)
        next_ver = max_ver + 1

        if next_ver > 99:
            raise ValueError("Recomputation depth ceiling of 99 exceeded. Halted to prevent data loops.")

        # Update input hash
        session.raw_input_manifest_hash = new_hash
        # Transition back to STAGED to reset calculations
        session.state = "STAGED"
        session.transition_to("COMPUTING")
        self.session_repo.save(session)

        # Deactivate old versions in same transaction block
        decision_id = new_inputs.get("decision_id", f"urn:decision:{session_id}")
        self.record_repo.deactivate_old_versions(decision_id, next_ver)

        daily_returns = new_inputs.get("daily_returns", [])
        daily_effects = new_inputs.get("daily_effects", {})
        strategy = self._get_strategy(session.compounding_strategy)
        new_records = []

        for asset_urn, effects_list in daily_effects.items():
            smoothed = strategy.compound_returns(daily_returns, effects_list)
            thesis_urn = new_inputs.get("thesis_urn", "urn:thesis:default")
            worker_urn = new_inputs.get("worker_urn", "urn:worker:default")
            capability_urn = new_inputs.get("capability_urn", "urn:capability:default")
            regime_urn = new_inputs.get("regime_urn", "urn:regime:default")

            record = PerformanceAttributionRecord(
                record_id=str(uuid.uuid4()),
                session_id=session_id,
                decision_id=decision_id,
                thesis_urn=thesis_urn,
                worker_urn=worker_urn,
                capability_urn=capability_urn,
                regime_urn=regime_urn,
                asset_urn=asset_urn,
                selection_return=smoothed.get("selection", Decimal("0.0")),
                allocation_return=smoothed.get("allocation", Decimal("0.0")),
                execution_return=smoothed.get("execution", Decimal("0.0")),
                beta_return=smoothed.get("beta", Decimal("0.0")),
                liquidation_tracking_residual=smoothed.get("residual", Decimal("0.0")),
                attribution_version=next_ver,
                is_active=True
            )
            self.record_repo.save(record)
            new_records.append(record)

            # Emit superseded event for each record
            for old_rec in old_records:
                if old_rec.asset_urn == asset_urn and old_rec.is_active:
                    # Mark as superseded
                    old_rec.is_active = False
                    
                    event_sup = AttributionSupersededEvent(
                        event_id=str(uuid.uuid4()),
                        correlation_id=session_id,
                        causation_id=recalculation_request_id,
                        record_id=old_rec.record_id,
                        old_version=old_rec.attribution_version,
                        new_version=next_ver,
                        superseded_at=datetime.utcnow()
                    )
                    self.events_list.append(event_sup)

        session.transition_to("CALIBRATED")
        self.session_repo.save(session)
        session.transition_to("SEALED")
        self.session_repo.save(session)

        # Emit recomputed session-level event
        event_re = AttributionRecomputedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=session_id,
            causation_id=recalculation_request_id,
            session_id=session_id,
            recomputed_at=datetime.utcnow()
        )
        self.events_list.append(event_re)
        return new_records


class AttributionInvalidationService:
    def __init__(
        self,
        session_repo: AttributionSessionRepository,
        record_repo: PerformanceAttributionRepository,
        events_list: Optional[List[Any]] = None
    ):
        self.session_repo = session_repo
        self.record_repo = record_repo
        self.events_list = events_list if events_list is not None else []

    def invalidate_session(self, session_id: str) -> AttributionInvalidatedEvent:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Deactivate all active records associated with this session
        self.record_repo.deactivate_by_session(session_id)

        event = AttributionInvalidatedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=session_id,
            causation_id=session_id,
            session_id=session_id,
            invalidated_at=datetime.utcnow()
        )
        self.events_list.append(event)
        return event


class AttributionReplayService:
    def __init__(
        self,
        session_repo: AttributionSessionRepository,
        record_repo: PerformanceAttributionRepository
    ):
        self.session_repo = session_repo
        self.record_repo = record_repo

    def replay_session(self, session_id: str, historical_inputs: dict) -> dict:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Check input manifest hash matches
        inputs_hash = CanonicalManifestSerializer.generate_hash(historical_inputs)
        if session.raw_input_manifest_hash != inputs_hash:
            raise ValueError("Input data mismatch against raw_input_manifest_hash. Replay failed.")

        # Re-run calculations dynamically
        daily_returns = historical_inputs.get("daily_returns", [])
        daily_effects = historical_inputs.get("daily_effects", {})
        
        # Compounding Math
        if session.compounding_strategy == "FRONGELLO":
            strategy = FrongelloCompounding()
        elif session.compounding_strategy == "CARINO":
            strategy = CarinoCompounding()
        elif session.compounding_strategy == "MENCHERO":
            strategy = MencheroCompounding()
        else:
            raise ValueError(f"Unknown strategy: {session.compounding_strategy}")

        replayed_results = {}
        for asset_urn, effects_list in daily_effects.items():
            replayed_results[asset_urn] = strategy.compound_returns(daily_returns, effects_list)

        # Cross-validate output matches saved records
        records = self.record_repo.find_by_session(session_id)
        for r in records:
            if r.is_active:
                rep_eff = replayed_results.get(r.asset_urn)
                if not rep_eff:
                    raise ValueError(f"Missing replayed results for asset {r.asset_urn}")
                # Verify return match
                if Decimal(str(rep_eff.get("selection", 0.0))) != r.selection_return:
                    raise ValueError(f"Replay output mismatch on selection effect for asset {r.asset_urn}")
                if Decimal(str(rep_eff.get("allocation", 0.0))) != r.allocation_return:
                    raise ValueError(f"Replay output mismatch on allocation effect for asset {r.asset_urn}")

        return {
            "session_id": session_id,
            "compounding_strategy": session.compounding_strategy,
            "raw_input_manifest_hash": session.raw_input_manifest_hash,
            "replayed_outputs": {k: {key: str(val) for key, val in v.items()} for k, v in replayed_results.items()}
        }
