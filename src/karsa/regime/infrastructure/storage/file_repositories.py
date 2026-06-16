import os
import json
import uuid
import threading
from typing import Optional, List
from pathlib import Path
from decimal import Decimal

from src.karsa.regime.domain.models import RegimeSession, RegimeSnapshot, RegimeTransition
from src.karsa.regime.domain.value_objects import RegimeClassification, SignalConfidenceScore
from src.karsa.regime.domain.repositories import (
    RegimeSessionRepository, RegimeSnapshotRepository, RegimeTransitionRepository,
    ConcurrencyError, ImmutableUpdateError
)
from src.karsa.regime.domain.lineage import reconstruct_transition_lineage, reconstruct_snapshot_lineage, LineageCycleError

def _atomic_write(file_path: Path, data: dict):
    temp_path = file_path.with_suffix(f'.tmp.{uuid.uuid4()}')
    try:
        with open(temp_path, 'w') as f:
            json.dump(data, f, sort_keys=True)
        # Atomic replace
        os.replace(temp_path, file_path)
    finally:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except OSError:
                pass

class FileRegimeSessionRepository(RegimeSessionRepository):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _get_path(self, session_urn: str) -> Path:
        safe_name = session_urn.replace(":", "_") + ".json"
        return self.base_path / safe_name

    def _serialize(self, session: RegimeSession) -> dict:
        return {
            "session_urn": session.session_urn,
            "state": session.state,
            "aggregate_version": session.aggregate_version
        }

    def _deserialize(self, data: dict) -> RegimeSession:
        return RegimeSession(
            session_urn=data["session_urn"],
            state=data["state"],
            aggregate_version=data["aggregate_version"]
        )

    def save(self, session: RegimeSession) -> None:
        with self._lock:
            existing = self.find_by_urn(session.session_urn)
            if existing:
                if session.aggregate_version != existing.aggregate_version + 1:
                    raise ConcurrencyError("OCC violation")
            else:
                if session.aggregate_version != 1:
                    raise ConcurrencyError("Initial version must be 1")
            
            _atomic_write(self._get_path(session.session_urn), self._serialize(session))

    def find_by_urn(self, session_urn: str) -> Optional[RegimeSession]:
        path = self._get_path(session_urn)
        if not path.exists():
            return None
        with open(path, 'r') as f:
            return self._deserialize(json.load(f))

    def find_paginated(self, limit: int, last_urn: Optional[str] = None) -> List[RegimeSession]:
        with self._lock:
            sessions = []
            for p in self.base_path.glob("*.json"):
                with open(p, 'r') as f:
                    sessions.append(self._deserialize(json.load(f)))
            
            urns = sorted([s.session_urn for s in sessions])
            if last_urn:
                urns = [u for u in urns if u > last_urn]
            
            selected = urns[:limit]
            return [s for s in sessions if s.session_urn in selected]

class FileRegimeSnapshotRepository(RegimeSnapshotRepository):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _get_path(self, snapshot_urn: str) -> Path:
        safe_name = snapshot_urn.replace(":", "_") + ".json"
        return self.base_path / safe_name

    def _serialize(self, snapshot: RegimeSnapshot) -> dict:
        return {
            "snapshot_urn": snapshot.snapshot_urn,
            "segment_urn": snapshot.segment_urn,
            "horizon_urn": snapshot.horizon_urn,
            "snapshot_date": snapshot.snapshot_date,
            "regime_classification": snapshot.regime_classification.to_dict(),
            "confidence_score": str(snapshot.confidence_score.value),
            "regime_manifest_hash": snapshot.regime_manifest_hash,
            "evidence_manifest_hash": snapshot.evidence_manifest_hash,
            "methodology_metadata": snapshot.methodology_metadata
        }

    def _deserialize(self, data: dict) -> RegimeSnapshot:
        c = RegimeClassification(**data["regime_classification"])
        score = SignalConfidenceScore(Decimal(data["confidence_score"]))
        return RegimeSnapshot(
            snapshot_urn=data["snapshot_urn"],
            segment_urn=data["segment_urn"],
            horizon_urn=data["horizon_urn"],
            snapshot_date=data["snapshot_date"],
            regime_classification=c,
            confidence_score=score,
            regime_manifest_hash=data["regime_manifest_hash"],
            evidence_manifest_hash=data["evidence_manifest_hash"],
            methodology_metadata=data["methodology_metadata"]
        )

    def save(self, snapshot: RegimeSnapshot) -> None:
        with self._lock:
            if self.find_by_urn(snapshot.snapshot_urn):
                raise ImmutableUpdateError("RegimeSnapshot is immutable")
            
            if self.find_by_natural_key(snapshot.segment_urn, snapshot.horizon_urn, snapshot.snapshot_date):
                raise ImmutableUpdateError("Natural key violation")

            _atomic_write(self._get_path(snapshot.snapshot_urn), self._serialize(snapshot))

    def find_by_urn(self, snapshot_urn: str) -> Optional[RegimeSnapshot]:
        path = self._get_path(snapshot_urn)
        if not path.exists():
            return None
        with open(path, 'r') as f:
            return self._deserialize(json.load(f))

    def find_by_natural_key(self, segment_urn: str, horizon_urn: str, snapshot_date: str) -> Optional[RegimeSnapshot]:
        with self._lock:
            for p in self.base_path.glob("*.json"):
                with open(p, 'r') as f:
                    s = self._deserialize(json.load(f))
                    if s.natural_key == (segment_urn, horizon_urn, snapshot_date):
                        return s
            return None

    def find_by_segment_paginated(self, segment_urn: str, limit: int, last_date: Optional[str] = None, last_urn: Optional[str] = None) -> List[RegimeSnapshot]:
        with self._lock:
            snaps = []
            for p in self.base_path.glob("*.json"):
                with open(p, 'r') as f:
                    s = self._deserialize(json.load(f))
                    if s.segment_urn == segment_urn:
                        snaps.append(s)
            
            snaps.sort(key=lambda s: (s.snapshot_date, s.snapshot_urn))
            if last_date is not None and last_urn is not None:
                snaps = [s for s in snaps if (s.snapshot_date, s.snapshot_urn) > (last_date, last_urn)]
            return snaps[:limit]

    def find_by_horizon_paginated(self, horizon_urn: str, limit: int, last_date: Optional[str] = None, last_urn: Optional[str] = None) -> List[RegimeSnapshot]:
        with self._lock:
            snaps = []
            for p in self.base_path.glob("*.json"):
                with open(p, 'r') as f:
                    s = self._deserialize(json.load(f))
                    if s.horizon_urn == horizon_urn:
                        snaps.append(s)
            
            snaps.sort(key=lambda s: (s.snapshot_date, s.snapshot_urn))
            if last_date is not None and last_urn is not None:
                snaps = [s for s in snaps if (s.snapshot_date, s.snapshot_urn) > (last_date, last_urn)]
            return snaps[:limit]

    def find_snapshot_lineage(self, start_urn: str) -> List[RegimeSnapshot]:
        s = self.find_by_urn(start_urn)
        return [s] if s else []

class FileRegimeTransitionRepository(RegimeTransitionRepository):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _get_path(self, transition_urn: str) -> Path:
        safe_name = transition_urn.replace(":", "_") + ".json"
        return self.base_path / safe_name

    def _serialize(self, transition: RegimeTransition) -> dict:
        return {
            "transition_urn": transition.transition_urn,
            "from_regime": transition.from_regime.to_dict(),
            "to_regime": transition.to_regime.to_dict(),
            "transition_manifest_hash": transition.transition_manifest_hash,
            "supersedes_transition_urn": transition.supersedes_transition_urn,
            "invalidates_transition_urn": transition.invalidates_transition_urn,
            "aggregate_version": transition.aggregate_version
        }

    def _deserialize(self, data: dict) -> RegimeTransition:
        return RegimeTransition(
            transition_urn=data["transition_urn"],
            from_regime=RegimeClassification(**data["from_regime"]),
            to_regime=RegimeClassification(**data["to_regime"]),
            transition_manifest_hash=data["transition_manifest_hash"],
            supersedes_transition_urn=data.get("supersedes_transition_urn"),
            invalidates_transition_urn=data.get("invalidates_transition_urn"),
            aggregate_version=data["aggregate_version"]
        )

    def save(self, transition: RegimeTransition) -> None:
        with self._lock:
            existing = self.find_by_urn(transition.transition_urn)
            if existing:
                if transition.aggregate_version != existing.aggregate_version + 1:
                    raise ConcurrencyError("OCC violation")
            else:
                if transition.aggregate_version != 1:
                    raise ConcurrencyError("Initial version must be 1")
            
            _atomic_write(self._get_path(transition.transition_urn), self._serialize(transition))

    def find_by_urn(self, transition_urn: str) -> Optional[RegimeTransition]:
        path = self._get_path(transition_urn)
        if not path.exists():
            return None
        with open(path, 'r') as f:
            return self._deserialize(json.load(f))

    def find_transition_lineage(self, start_urn: str) -> List[RegimeTransition]:
        with self._lock:
            transitions = []
            for p in self.base_path.glob("*.json"):
                with open(p, 'r') as f:
                    transitions.append(self._deserialize(json.load(f)))
            return reconstruct_transition_lineage(transitions, start_urn)
