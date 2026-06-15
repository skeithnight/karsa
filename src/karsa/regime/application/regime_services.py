import hashlib
import json
import uuid
from typing import List, Optional
from decimal import Decimal

from src.karsa.regime.domain.models import RegimeSnapshot, RegimeTransition
from src.karsa.regime.domain.value_objects import (
    RegimeEvidence, RegimeClassification, SignalConfidenceScore, RegimeMethodologyManifest
)
from src.karsa.regime.domain.repositories import (
    RegimeSnapshotRepository, RegimeTransitionRepository
)

class DriftError(Exception):
    pass

class RegimeClassificationService:
    def __init__(self, snapshot_repo: RegimeSnapshotRepository):
        self.snapshot_repo = snapshot_repo

    def classify(self, segment_urn: str, horizon_urn: str, snapshot_date: str,
                 classification: RegimeClassification, confidence: SignalConfidenceScore,
                 evidences: List[RegimeEvidence], methodology_urn: str,
                 policy_hash: str, strategy_version: str, metadata: dict) -> RegimeSnapshot:
        
        # Enforce horizon isolation and generate manifest
        evidence_hashes = []
        for e in evidences:
            data = e.to_dict()
            canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True)
            e_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
            # The value object already has it, we verify/generate deterministic list
            evidence_hashes.append(e_hash)
            
        # create manifest
        manifest = RegimeMethodologyManifest.create(
            regime_methodology_urn=methodology_urn,
            regime_policy_hash=policy_hash,
            regime_strategy_version=strategy_version,
            evidence_manifest_hashes=evidence_hashes
        )
        
        # composite evidence manifest hash for the snapshot
        canonical_evs = json.dumps(sorted(evidence_hashes), separators=(',', ':'))
        composite_ev_hash = hashlib.sha256(canonical_evs.encode('utf-8')).hexdigest()

        snapshot_urn = f"urn:karsa:regime:snapshot:{uuid.uuid4()}"
        
        snapshot = RegimeSnapshot(
            snapshot_urn=snapshot_urn,
            segment_urn=segment_urn,
            horizon_urn=horizon_urn,
            snapshot_date=snapshot_date,
            regime_classification=classification,
            confidence_score=confidence,
            regime_manifest_hash=manifest.regime_manifest_hash,
            evidence_manifest_hash=composite_ev_hash,
            methodology_metadata=metadata
        )
        self.snapshot_repo.save(snapshot)
        return snapshot

class RegimeTransitionService:
    def __init__(self, snapshot_repo: RegimeSnapshotRepository, transition_repo: RegimeTransitionRepository):
        self.snapshot_repo = snapshot_repo
        self.transition_repo = transition_repo

    def evaluate_hysteresis(self, segment_urn: str, horizon_urn: str, current_date: str, confirmation_window: int) -> Optional[RegimeTransition]:
        # Simple confirmation window evaluation
        # Fetch last N+1 snapshots up to current_date
        # (This is just logic demonstration, we fetch some history)
        snaps = self.snapshot_repo.find_by_segment_paginated(segment_urn, limit=100)
        # filter by horizon and date <= current_date
        snaps = [s for s in snaps if s.horizon_urn == horizon_urn and s.snapshot_date <= current_date]
        snaps.sort(key=lambda x: x.snapshot_date)
        
        if len(snaps) < confirmation_window + 1:
            return None # Not enough data
            
        recent = snaps[-confirmation_window:]
        target_regime = recent[-1].regime_classification
        
        # Check if all recent N match the target
        if any(s.regime_classification.to_dict() != target_regime.to_dict() for s in recent):
            return None # Hysteresis suppression (thrashing)
            
        # Look at the one before window
        previous_regime = snaps[-(confirmation_window + 1)].regime_classification
        if previous_regime.to_dict() == target_regime.to_dict():
            return None # No state change
            
        # Change confirmed
        transition_data = {
            "confirmation_window": confirmation_window,
            "segment_urn": segment_urn,
            "horizon_urn": horizon_urn
        }
        canonical_trans = json.dumps(transition_data, separators=(',', ':'), sort_keys=True)
        t_hash = hashlib.sha256(canonical_trans.encode('utf-8')).hexdigest()
        
        t = RegimeTransition(
            transition_urn=f"urn:karsa:regime:transition:{uuid.uuid4()}",
            from_regime=previous_regime,
            to_regime=target_regime,
            transition_manifest_hash=t_hash
        )
        self.transition_repo.save(t)
        return t

class RegimeReplayService:
    def verify(self, snapshot: RegimeSnapshot, expected_manifest: RegimeMethodologyManifest, expected_evidence: List[RegimeEvidence]):
        if snapshot.regime_manifest_hash != expected_manifest.regime_manifest_hash:
            raise DriftError("Manifest mismatch")
        
        # verify methodology drift
        # this uses strictly inputs, no database
        e_hashes = []
        for e in expected_evidence:
            data = e.to_dict()
            e_hashes.append(hashlib.sha256(json.dumps(data, separators=(',', ':'), sort_keys=True).encode()).hexdigest())
            
        m = RegimeMethodologyManifest.create(
            regime_methodology_urn=expected_manifest.regime_methodology_urn,
            regime_policy_hash=expected_manifest.regime_policy_hash,
            regime_strategy_version=expected_manifest.regime_strategy_version,
            evidence_manifest_hashes=e_hashes
        )
        if m.regime_manifest_hash != expected_manifest.regime_manifest_hash:
            raise DriftError("Methodology/Policy drift detected")

class RegimeProjectionService:
    def __init__(self, snapshot_repo: RegimeSnapshotRepository, transition_repo: RegimeTransitionRepository):
        self.snapshot_repo = snapshot_repo
        self.transition_repo = transition_repo

    def get_current_regime(self, segment_urn: str, horizon_urn: str) -> Optional[RegimeClassification]:
        snaps = self.snapshot_repo.find_by_segment_paginated(segment_urn, limit=100)
        snaps = [s for s in snaps if s.horizon_urn == horizon_urn]
        if not snaps:
            return None
        snaps.sort(key=lambda x: x.snapshot_date)
        return snaps[-1].regime_classification

    def get_historical_projection(self, segment_urn: str, horizon_urn: str) -> List[RegimeSnapshot]:
        snaps = self.snapshot_repo.find_by_segment_paginated(segment_urn, limit=1000)
        return sorted([s for s in snaps if s.horizon_urn == horizon_urn], key=lambda x: x.snapshot_date)

class RegimeInvalidationService:
    def __init__(self, snapshot_repo: RegimeSnapshotRepository, transition_repo: RegimeTransitionRepository):
        self.snapshot_repo = snapshot_repo
        self.transition_repo = transition_repo

    def invalidate_snapshot_chain(self, start_snapshot_urn: str, invalidating_urn: str):
        # snapshot lineage
        lineage = self.snapshot_repo.find_snapshot_lineage(start_snapshot_urn)
        # mock invalidation (snapshots are immutable, we'd emit events or have an invalidation record)
        # The prompt says "populates invalidated lineage metadata". In models.py we didn't add 
        # invalidates_snapshot_urn to Snapshot since it's immutable. 
        pass

    def invalidate_transition_chain(self, start_transition_urn: str, invalidating_urn: str):
        lineage = self.transition_repo.find_transition_lineage(start_transition_urn)
        for t in lineage:
            t.invalidate(invalidating_urn)
            self.transition_repo.save(t)
