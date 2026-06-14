import os
import json
from typing import Optional, List, Dict
from karsa.performance.domain.model.evaluation import DecisionEvaluation, EvaluationSnapshot
from karsa.performance.domain.model.repositories import (
    DecisionEvaluationRepository,
    EvaluationSnapshotRepository
)
from karsa.performance.domain.model.value_objects import EvaluationTarget

class ConcurrencyConflictError(Exception):
    pass

class InMemoryDecisionEvaluationRepository(DecisionEvaluationRepository):
    def __init__(self):
        self._evaluations: Dict[str, DecisionEvaluation] = {}

    def save(self, evaluation: DecisionEvaluation) -> None:
        existing = self._evaluations.get(evaluation.decision_id)
        if existing:
            if existing.aggregate_version != evaluation.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing.aggregate_version}, got {evaluation.aggregate_version - 1}"
                )
        self._evaluations[evaluation.decision_id] = evaluation

    def find_by_decision(self, decision_id: str) -> Optional[DecisionEvaluation]:
        return self._evaluations.get(decision_id)

    def list_all(self) -> List[DecisionEvaluation]:
        return list(self._evaluations.values())

    def clear(self) -> None:
        self._evaluations.clear()


class InMemoryEvaluationSnapshotRepository(EvaluationSnapshotRepository):
    def __init__(self):
        self._snapshots: Dict[str, EvaluationSnapshot] = {}

    def save(self, snapshot: EvaluationSnapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot

    def find_by_id(self, snapshot_id: str) -> Optional[EvaluationSnapshot]:
        return self._snapshots.get(snapshot_id)

    def list_by_target(self, target: EvaluationTarget) -> List[EvaluationSnapshot]:
        return [
            s for s in self._snapshots.values()
            if s.target.target_type == target.target_type and s.target.target_id == target.target_id
        ]

    def list_all(self) -> List[EvaluationSnapshot]:
        return list(self._snapshots.values())

    def clear(self) -> None:
        self._snapshots.clear()


class FileDecisionEvaluationRepository(DecisionEvaluationRepository):
    def __init__(self, storage_dir: str = ".karsa/performance/evaluations/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, decision_id: str) -> str:
        return os.path.join(self.storage_dir, f"{decision_id}.json")

    def save(self, evaluation: DecisionEvaluation) -> None:
        path = self._get_path(evaluation.decision_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_data = json.load(f)
            existing_ver = existing_data.get("aggregate_version", 1)
            if existing_ver != evaluation.aggregate_version - 1:
                raise ConcurrencyConflictError(
                    f"OCC Conflict: Expected version {existing_ver}, got {evaluation.aggregate_version - 1}"
                )
        
        with open(path, "w") as f:
            json.dump(evaluation.to_dict(), f, indent=2)

    def find_by_decision(self, decision_id: str) -> Optional[DecisionEvaluation]:
        path = self._get_path(decision_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return DecisionEvaluation.from_dict(data)

    def list_all(self) -> List[DecisionEvaluation]:
        evaluations = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    evaluations.append(DecisionEvaluation.from_dict(data))
                except Exception:
                    pass
        return evaluations

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass


class FileEvaluationSnapshotRepository(EvaluationSnapshotRepository):
    def __init__(self, storage_dir: str = ".karsa/performance/snapshots/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, snapshot_id: str) -> str:
        return os.path.join(self.storage_dir, f"{snapshot_id}.json")

    def save(self, snapshot: EvaluationSnapshot) -> None:
        path = self._get_path(snapshot.snapshot_id)
        with open(path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def find_by_id(self, snapshot_id: str) -> Optional[EvaluationSnapshot]:
        path = self._get_path(snapshot_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return EvaluationSnapshot.from_dict(data)

    def list_by_target(self, target: EvaluationTarget) -> List[EvaluationSnapshot]:
        snapshots = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    snap = EvaluationSnapshot.from_dict(data)
                    if snap.target.target_type == target.target_type and snap.target.target_id == target.target_id:
                        snapshots.append(snap)
                except Exception:
                    pass
        return snapshots

    def list_all(self) -> List[EvaluationSnapshot]:
        snapshots = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    snapshots.append(EvaluationSnapshot.from_dict(data))
                except Exception:
                    pass
        return snapshots

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass
