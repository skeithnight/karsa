import json
import os
from typing import List, Optional
from karsa.thesis.domain.models import Thesis, ThesisSnapshot, ThesisTransition, ThesisAssumptionIdentity, ThesisAssumptionVersion
from karsa.thesis.domain.value_objects import LifecycleState, AssumptionLifecycleState
from karsa.thesis.infrastructure.storage.memory_repo import (
    InMemoryThesisRepository, InMemoryThesisSnapshotRepository, InMemoryThesisTransitionRepository,
    InMemoryAssumptionIdentityRepository, InMemoryAssumptionVersionRepository
)

class FileThesisRepository(InMemoryThesisRepository):
    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._load_all()

    def _load_all(self):
        for f_name in os.listdir(self.directory):
            if f_name.endswith('.json'):
                with open(os.path.join(self.directory, f_name), 'r') as f:
                    data = json.load(f)
                    t = Thesis(data['thesis_urn'], data['current_snapshot_urn'], LifecycleState(data['current_status']), data['aggregate_version'])
                    self._db[t.thesis_urn] = t

    def save(self, thesis: Thesis) -> None:
        super().save(thesis)
        with open(os.path.join(self.directory, f"{thesis.thesis_urn}.json"), "w") as f:
            json.dump({
                "thesis_urn": thesis.thesis_urn,
                "current_snapshot_urn": thesis.current_snapshot_urn,
                "current_status": thesis.current_status.value,
                "aggregate_version": thesis.aggregate_version
            }, f)


class FileThesisSnapshotRepository(InMemoryThesisSnapshotRepository):
    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._load_all()

    def _load_all(self):
        for f_name in os.listdir(self.directory):
            if f_name.endswith('.json'):
                with open(os.path.join(self.directory, f_name), 'r') as f:
                    data = json.load(f)
                    s = ThesisSnapshot(data['snapshot_urn'], data['snapshot_version'], LifecycleState(data['lifecycle_state']),
                                       data['origin_regime_snapshot_urn'], data.get('supersedes_snapshot_urn'), data.get('invalidates_snapshot_urn'), [])
                    self._db[s.snapshot_urn] = s

    def save(self, snapshot: ThesisSnapshot) -> None:
        super().save(snapshot)
        with open(os.path.join(self.directory, f"{snapshot.snapshot_urn}.json"), "w") as f:
            json.dump({
                "snapshot_urn": snapshot.snapshot_urn,
                "snapshot_version": snapshot.snapshot_version,
                "lifecycle_state": snapshot.lifecycle_state.value,
                "origin_regime_snapshot_urn": snapshot.origin_regime_snapshot_urn,
                "supersedes_snapshot_urn": snapshot.supersedes_snapshot_urn,
                "invalidates_snapshot_urn": snapshot.invalidates_snapshot_urn
            }, f)


class FileThesisTransitionRepository(InMemoryThesisTransitionRepository):
    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._load_all()

    def _load_all(self):
        from karsa.thesis.domain.models import ThesisDelta
        for f_name in os.listdir(self.directory):
            if f_name.endswith('.json'):
                with open(os.path.join(self.directory, f_name), 'r') as f:
                    data = json.load(f)
                    d_data = data['delta']
                    delta = ThesisDelta(d_data['delta_urn'], d_data['delta_manifest_hash'], d_data['added_assumptions'], d_data['removed_assumptions'])
                    t = ThesisTransition(data['transition_urn'], data.get('supersedes_transition_urn'), data.get('invalidates_transition_urn'), delta)
                    self._db[t.transition_urn] = t

    def save(self, transition: ThesisTransition) -> None:
        super().save(transition)
        with open(os.path.join(self.directory, f"{transition.transition_urn}.json"), "w") as f:
            json.dump({
                "transition_urn": transition.transition_urn,
                "supersedes_transition_urn": transition.supersedes_transition_urn,
                "invalidates_transition_urn": transition.invalidates_transition_urn,
                "delta": {
                    "delta_urn": transition.delta.delta_urn,
                    "delta_manifest_hash": transition.delta.delta_manifest_hash,
                    "added_assumptions": transition.delta.added_assumptions,
                    "removed_assumptions": transition.delta.removed_assumptions
                }
            }, f)


class FileAssumptionIdentityRepository(InMemoryAssumptionIdentityRepository):
    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._load_all()

    def _load_all(self):
        for f_name in os.listdir(self.directory):
            if f_name.endswith('.json'):
                with open(os.path.join(self.directory, f_name), 'r') as f:
                    data = json.load(f)
                    i = ThesisAssumptionIdentity(data['assumption_urn'])
                    self._db[i.assumption_urn] = i

    def save(self, identity: ThesisAssumptionIdentity) -> None:
        super().save(identity)
        with open(os.path.join(self.directory, f"{identity.assumption_urn}.json"), "w") as f:
            json.dump({"assumption_urn": identity.assumption_urn}, f)


class FileAssumptionVersionRepository(InMemoryAssumptionVersionRepository):
    def __init__(self, directory: str):
        super().__init__()
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._load_all()

    def _load_all(self):
        from karsa.thesis.domain.value_objects import CalibrationReference
        for f_name in os.listdir(self.directory):
            if f_name.endswith('.json'):
                with open(os.path.join(self.directory, f_name), 'r') as f:
                    data = json.load(f)
                    cal = CalibrationReference(data['cal_urn'], data['cal_hash']) if data.get('cal_urn') else None
                    v = ThesisAssumptionVersion(
                        data['assumption_urn'], data['assumption_version'], data['assumption_statement'],
                        data['raw_confidence'], AssumptionLifecycleState(data['lifecycle_state']),
                        data['assumption_manifest_hash'], cal
                    )
                    self._db[data['key']] = v

    def save(self, version: ThesisAssumptionVersion) -> None:
        super().save(version)
        key = f"{version.assumption_urn}_{version.assumption_version}"
        cal_urn = version.calibrated_confidence_reference.calibration_urn if version.calibrated_confidence_reference else None
        cal_hash = version.calibrated_confidence_reference.calibration_manifest_hash if version.calibrated_confidence_reference else None
        with open(os.path.join(self.directory, f"{key}.json"), "w") as f:
            json.dump({
                "key": key,
                "assumption_urn": version.assumption_urn,
                "assumption_version": version.assumption_version,
                "assumption_statement": version.assumption_statement,
                "raw_confidence": version.raw_confidence,
                "lifecycle_state": version.lifecycle_state.value,
                "assumption_manifest_hash": version.assumption_manifest_hash,
                "cal_urn": cal_urn,
                "cal_hash": cal_hash
            }, f)
