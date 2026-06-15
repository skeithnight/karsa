import json
import hashlib
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from karsa.allocation.domain.value_objects import (
    PortfolioHorizon,
    AllocationScore,
    RiskBudgetAssignment,
    AllocationRecommendation,
    AllocationMethodologyManifest
)
from karsa.allocation.domain.models import (
    AllocationSession,
    AllocationDecisionRecord,
    ImmutabilityViolationError
)
from karsa.allocation.domain.events import (
    AllocationCalculatedEvent,
    AllocationSupersededEvent,
    AllocationInvalidatedEvent
)
from karsa.allocation.infrastructure.storage.in_memory_repositories import ConcurrencyConflictError

class MethodologyDriftException(Exception):
    pass

class ReplayIntegrityException(Exception):
    pass

@dataclass(frozen=True)
class RankedWorker:
    worker_urn: str
    rank_index: int
    allocation_score: float

@dataclass
class RankingProjection:
    session_urn: str
    horizon: PortfolioHorizon
    rankings: List[RankedWorker]
    calculated_at: datetime


class AllocationCalculationService:
    def __init__(self, record_repo, session_repo, events_publisher: Optional[List[Any]] = None):
        self.record_repo = record_repo
        self.session_repo = session_repo
        self.events_publisher = events_publisher if events_publisher is not None else []

    def calculate_allocations(
        self,
        session_urn: str,
        worker_urn: str,
        decision_id: str,
        raw_score: float,
        brier_score: float,
        selection_return: float,
        review_score: float,
        has_warning: bool,
        allocation_methodology_urn: str,
        allocation_policy_hash: str,
        allocation_strategy_version: str,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> AllocationDecisionRecord:
        # 1. Validate session
        session = self.session_repo.find_by_urn(session_urn)
        if not session:
            raise ValueError(f"AllocationSession not found for URN: {session_urn}")
        if session.status != "CALCULATING":
            raise ValueError(f"AllocationSession is not in CALCULATING status (current: {session.status})")

        # 2. Score calculations
        # performance_score: lower Brier is better. Capped at [0.0, 1.0]
        perf_score = max(0.0, min(1.0, 1.0 - brier_score))
        # attribution_score: higher selection return is better
        attr_score = max(0.0, 1.0 + selection_return)
        # penalty multiplier: 0.5 if warning, else 1.0
        penalty = 0.5 if has_warning else 1.0

        score = AllocationScore(
            raw_score=raw_score,
            performance_score=perf_score,
            attribution_score=attr_score,
            review_penalty_multiplier=penalty
        )

        # 3. Weight calculation
        weight = raw_score * perf_score * attr_score * penalty
        cap_pct = weight * 0.8
        risk = RiskBudgetAssignment(
            tracking_error_pct=weight * 0.1,
            max_drawdown_limit=weight * 0.3
        )
        recommendation = AllocationRecommendation(
            recommended_weight=weight,
            recommended_capital_percentage=cap_pct,
            risk_budget=risk
        )

        # 4. Methodology manifest hash
        manifest = AllocationMethodologyManifest(
            allocation_methodology_urn=allocation_methodology_urn,
            allocation_policy_hash=allocation_policy_hash,
            allocation_strategy_version=allocation_strategy_version
        )
        manifest_hash = manifest.compute_hash()

        # Retry loop for OCC conflicts
        attempt = 0
        while True:
            try:
                # 5. Check for existing active record to supersede
                existing_active = self.record_repo.find_active_by_worker(worker_urn, limit=100)
                superseded_record = None
                for old_rec in existing_active:
                    if old_rec.decision_id == decision_id and old_rec.is_active:
                        superseded_record = old_rec
                        break

                record_id = str(uuid.uuid4())
                new_version = 1
                supersedes_urn = None

                if superseded_record:
                    # Immutability validation (superseding)
                    superseded_record.supersede(next_version=superseded_record.allocation_version + 1)
                    self.record_repo.save(superseded_record)
                    
                    new_version = superseded_record.allocation_version + 1
                    supersedes_urn = superseded_record.record_urn

                record = AllocationDecisionRecord(
                    record_id=record_id,
                    record_urn=f"urn:karsa:allocation:record:{record_id}",
                    session_urn=session_urn,
                    worker_urn=worker_urn,
                    decision_id=decision_id,
                    horizon=session.horizon,
                    allocation_score=score,
                    recommendation=recommendation,
                    allocation_methodology_urn=allocation_methodology_urn,
                    allocation_policy_hash=allocation_policy_hash,
                    allocation_strategy_version=allocation_strategy_version,
                    allocation_manifest_hash=manifest_hash,
                    supersedes_record_urn=supersedes_urn,
                    is_active=True,
                    allocation_version=new_version
                )
                self.record_repo.save(record)
                break
            except ConcurrencyConflictError as e:
                attempt += 1
                if attempt >= 3:
                    raise e

        # 6. Publish events
        now = datetime.now(timezone.utc)
        if superseded_record:
            super_evt = AllocationSupersededEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=correlation_id or session_urn,
                causation_id=causation_id or record.record_id,
                occurred_at=now,
                schema_version=1,
                record_urn=superseded_record.record_urn,
                superseded_by_record_urn=record.record_urn,
                allocation_version=record.allocation_version
            )
            self.events_publisher.append(super_evt)

        calc_evt = AllocationCalculatedEvent(
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id or session_urn,
            causation_id=causation_id or record.record_id,
            occurred_at=now,
            schema_version=1,
            record_urn=record.record_urn,
            session_urn=record.session_urn,
            worker_urn=record.worker_urn,
            decision_id=record.decision_id,
            recommended_weight=weight,
            allocation_version=record.allocation_version
        )
        self.events_publisher.append(calc_evt)

        return record


class RankingProjectionService:
    def build_ranking_projection(
        self,
        session_urn: str,
        horizon: PortfolioHorizon,
        records: List[AllocationDecisionRecord],
        brier_scores: Dict[str, float],
        selection_returns: Dict[str, float],
        review_scores: Dict[str, float]
    ) -> RankingProjection:
        # Filter active records for this session and horizon
        matched = []
        for r in records:
            if r.session_urn == session_urn and r.horizon.horizon_id == horizon.horizon_id and r.is_active:
                matched.append(r)

        # Deterministic sorting function
        def sort_key(record: AllocationDecisionRecord):
            score_val = record.allocation_score.raw_score
            b_score = brier_scores.get(record.worker_urn, 1.0)
            s_return = selection_returns.get(record.worker_urn, 0.0)
            r_score = review_scores.get(record.worker_urn, 0.0)
            return (-score_val, b_score, -s_return, -r_score, record.worker_urn)

        matched.sort(key=sort_key)

        rankings = []
        for index, r in enumerate(matched):
            rankings.append(
                RankedWorker(
                    worker_urn=r.worker_urn,
                    rank_index=index + 1,
                    allocation_score=r.allocation_score.raw_score
                )
            )

        return RankingProjection(
            session_urn=session_urn,
            horizon=horizon,
            rankings=rankings,
            calculated_at=datetime.now(timezone.utc)
        )


class AllocationReplayService:
    def __init__(self, record_repo):
        self.record_repo = record_repo

    def verify_replay(
        self,
        record_urn: str,
        pinned_manifest: AllocationMethodologyManifest
    ) -> bool:
        # Load the decision record
        record = self.record_repo.find_by_urn(record_urn)
        if not record:
            raise ValueError(f"AllocationDecisionRecord not found for URN: {record_urn}")

        # 1. Verify manifest URN metadata matches record fields
        if record.allocation_methodology_urn != pinned_manifest.allocation_methodology_urn:
            raise MethodologyDriftException("Methodology URN drift detected")
        if record.allocation_policy_hash != pinned_manifest.allocation_policy_hash:
            raise MethodologyDriftException("Policy hash drift detected")
        if record.allocation_strategy_version != pinned_manifest.allocation_strategy_version:
            raise MethodologyDriftException("Strategy version drift detected")

        # 2. Recompute manifest hash from pinned metadata
        computed_hash = pinned_manifest.compute_hash()
        if computed_hash != record.allocation_manifest_hash:
            raise ReplayIntegrityException(
                f"Replay manifest hash mismatch! Record: {record.allocation_manifest_hash}, Computed: {computed_hash}"
            )

        return True


class AllocationInvalidationService:
    def __init__(self, record_repo, events_publisher: Optional[List[Any]] = None):
        self.record_repo = record_repo
        self.events_publisher = events_publisher if events_publisher is not None else []

    def invalidate_lineage(
        self,
        start_record_urn: str,
        invalidating_version: int,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> List[AllocationDecisionRecord]:
        lineage = self.record_repo.find_lineage(start_record_urn)
        invalidated_records = []
        now = datetime.now(timezone.utc)

        for record in lineage:
            if record.is_active:
                record.invalidate(invalidating_version)
                self.record_repo.save(record)
                invalidated_records.append(record)

                evt = AllocationInvalidatedEvent(
                    event_id=str(uuid.uuid4()),
                    correlation_id=correlation_id or record.session_urn,
                    causation_id=causation_id or record.record_id,
                    occurred_at=now,
                    schema_version=1,
                    record_urn=record.record_urn,
                    invalidated_by_version=invalidating_version
                )
                self.events_publisher.append(evt)

        return invalidated_records
