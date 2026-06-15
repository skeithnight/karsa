import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from karsa.performance.domain.model.models import PerformanceSession, WorkerEvaluationRecord
from karsa.performance.domain.model.repositories import PerformanceSessionRepository, WorkerEvaluationRepository
from karsa.performance.domain.model.value_objects import (
    BrierScore,
    CalibrationBin,
    CalibrationCurve,
    CanonicalManifestSerializer
)
from karsa.performance.events.events import (
    PerformanceSessionStagedEvent,
    PerformanceSessionEvaluatedEvent,
    PerformanceSessionSealedEvent,
    BrierScoreCalibratedEvent
)

class PerformanceEvaluationService:
    def __init__(
        self,
        session_repo: PerformanceSessionRepository,
        record_repo: WorkerEvaluationRepository,
        events_list: Optional[List[Any]] = None
    ):
        self.session_repo = session_repo
        self.record_repo = record_repo
        self.events_list = events_list if events_list is not None else []

    def stage_session(self, session_id: str, horizon_start: datetime, horizon_end: datetime) -> PerformanceSession:
        existing = self.session_repo.get_by_id(session_id)
        if existing:
            raise ValueError(f"Performance session already exists: {session_id}")
            
        session = PerformanceSession(
            session_id=session_id,
            horizon_start=horizon_start,
            horizon_end=horizon_end,
            state="STAGED",
            raw_input_manifest_hash=""
        )
        self.session_repo.save(session)
        
        self.events_list.append(PerformanceSessionStagedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            session_id=session_id,
            staged_at=datetime.now(timezone.utc)
        ))
        return session

    def evaluate_performance(self, session_id: str, inputs: dict) -> List[WorkerEvaluationRecord]:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
            
        session.transition_to("EVALUATING")
        self.session_repo.save(session)
        
        manifest_hash = CanonicalManifestSerializer.generate_hash(inputs)
        
        records = []
        forecasts = inputs.get("forecasts", [])
        
        for f in forecasts:
            rid = f.get("record_id", str(uuid.uuid4()))
            decision_id = f["decision_id"]
            worker_urn = f["worker_urn"]
            asset_urn = f["asset_urn"]
            regime_urn = f.get("regime_urn", "urn:regime:neutral")
            prob = Decimal(str(f["forecast_probability"]))
            outcome = int(f["realized_outcome"])
            ret = Decimal(str(f.get("realized_return", "0.0")))
            
            # Brier Score component
            brier_comp = (prob - Decimal(outcome)) ** 2
            
            # Fetch existing to find next version
            existing_records = self.record_repo.find_active_by_worker(worker_urn)
            decision_existing = [r for r in existing_records if r.decision_id == decision_id]
            next_ver = 1
            if decision_existing:
                next_ver = max(r.evaluation_version for r in decision_existing) + 1
                
            record = WorkerEvaluationRecord(
                record_id=rid,
                session_id=session_id,
                decision_id=decision_id,
                worker_urn=worker_urn,
                asset_urn=asset_urn,
                regime_urn=regime_urn,
                forecast_probability=prob,
                realized_outcome=outcome,
                brier_score_component=brier_comp,
                realized_return=ret,
                evaluation_version=next_ver,
                is_active=True
            )
            self.record_repo.save(record)
            records.append(record)
            
            if next_ver > 1:
                self.record_repo.deactivate_old_versions(decision_id, next_ver)

        session.transition_to("CALIBRATED")
        session.raw_input_manifest_hash = manifest_hash
        self.session_repo.save(session)
        
        # Calculate calibrations
        calibrations = []
        worker_records: Dict[str, List[WorkerEvaluationRecord]] = {}
        for r in records:
            worker_records.setdefault(r.worker_urn, []).append(r)
            
        for worker, recs in worker_records.items():
            avg_brier = sum(r.brier_score_component for r in recs) / len(recs)
            calibrations.append({
                "worker_urn": worker,
                "brier_score": str(avg_brier),
                "forecast_count": len(recs),
                "calibration_multiplier": str(Decimal("1.0") - avg_brier)
            })

        self.events_list.append(PerformanceSessionEvaluatedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            session_id=session_id,
            evaluated_at=datetime.now(timezone.utc),
            records=[r.to_dict() for r in records]
        ))
        
        self.events_list.append(BrierScoreCalibratedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            session_id=session_id,
            calibrated_at=datetime.now(timezone.utc),
            calibrations=calibrations
        ))
        
        return records

    def seal_session(self, session_id: str) -> PerformanceSession:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
            
        session.transition_to("SEALED")
        self.session_repo.save(session)
        
        self.events_list.append(PerformanceSessionSealedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            session_id=session_id,
            sealed_at=datetime.now(timezone.utc)
        ))
        return session

    def recompute_performance(self, session_id: str, inputs: dict, request_id: str) -> List[WorkerEvaluationRecord]:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
            
        
        # Insert new calculations
        session.transition_to("STAGED")
        self.session_repo.save(session)
        
        return self.evaluate_performance(session_id, inputs)


class PerformanceReplayService:
    def __init__(self, session_repo: PerformanceSessionRepository, record_repo: WorkerEvaluationRepository):
        self.session_repo = session_repo
        self.record_repo = record_repo

    def replay_session(self, session_id: str, historical_inputs: dict) -> bool:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
            
        new_hash = CanonicalManifestSerializer.generate_hash(historical_inputs)
        if new_hash != session.raw_input_manifest_hash:
            raise ValueError("Manifest hash mismatch during replay")
            
        records = self.record_repo.find_by_session(session_id)
        
        # Verify correctness of calculations
        forecasts = historical_inputs.get("forecasts", [])
        for f in forecasts:
            worker_urn = f["worker_urn"]
            decision_id = f["decision_id"]
            prob = Decimal(str(f["forecast_probability"]))
            outcome = int(f["realized_outcome"])
            expected_brier = (prob - Decimal(outcome)) ** 2
            
            matching = [r for r in records if r.decision_id == decision_id and r.worker_urn == worker_urn]
            if not matching:
                raise ValueError(f"Missing evaluation record for worker {worker_urn} decision {decision_id}")
                
            # Check latest version Brier component
            latest = max(matching, key=lambda x: x.evaluation_version)
            if latest.brier_score_component != expected_brier:
                raise ValueError(f"Replay Brier score component mismatch for worker {worker_urn}: expected {expected_brier}, got {latest.brier_score_component}")
                
        return True


class CalibrationProjectionService:
    def __init__(self, record_repo: WorkerEvaluationRepository):
        self.record_repo = record_repo

    def get_calibrated_confidence(self, worker_urn: str, raw_confidence: Decimal, regime_urn: str) -> Decimal:
        records = self.record_repo.find_active_by_worker(worker_urn)
        regime_records = [r for r in records if r.regime_urn == regime_urn]
        
        if not regime_records:
            return raw_confidence
            
        avg_brier = sum(r.brier_score_component for r in regime_records) / len(regime_records)
        return raw_confidence * (Decimal("1.0") - avg_brier)

    def build_calibration_curve(self, worker_urn: str, regime_urn: str) -> CalibrationCurve:
        records = self.record_repo.find_active_by_worker(worker_urn)
        regime_records = [r for r in records if r.regime_urn == regime_urn]
        
        bins = []
        for i in range(10):
            start = Decimal(str(i / 10.0))
            end = Decimal(str((i + 1) / 10.0))
            
            bin_recs = []
            for r in regime_records:
                # Group based on forecast confidence bins
                # Left-inclusive, right-exclusive, except for the last bin (i=9) which is right-inclusive.
                if i == 9:
                    in_bin = start <= r.forecast_probability <= end
                else:
                    in_bin = start <= r.forecast_probability < end
                    
                if in_bin:
                    bin_recs.append(r)
                    
            pred_count = len(bin_recs)
            succ_count = sum(1 for r in bin_recs if r.realized_outcome == 1)
            
            calib_prob = Decimal("0.0")
            if pred_count > 0:
                calib_prob = Decimal(succ_count) / Decimal(pred_count)
            else:
                calib_prob = (start + end) / Decimal("2.0")
                
            bins.append(CalibrationBin(start, end, pred_count, succ_count, calib_prob))
            
        return CalibrationCurve(bins)
