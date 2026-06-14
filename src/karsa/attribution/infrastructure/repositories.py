import os
import json
from typing import Optional, List, Dict
from karsa.attribution.domain.model.models import AttributionRecord, AttributionAdjustment
from karsa.attribution.domain.model.repositories import AttributionRecordRepository, AttributionAdjustmentRepository

class InMemoryAttributionRecordRepository(AttributionRecordRepository):
    def __init__(self):
        self._records: Dict[str, AttributionRecord] = {}

    def save(self, record: AttributionRecord) -> None:
        self._records[record.attribution_id] = record

    def find_by_attribution_id(self, attr_id: str) -> Optional[AttributionRecord]:
        return self._records.get(attr_id)

    def find_by_execution_id(self, exec_id: str) -> Optional[AttributionRecord]:
        for r in self._records.values():
            if r.execution_id == exec_id:
                return r
        return None

    def list_all(self) -> List[AttributionRecord]:
        return list(self._records.values())

    def clear(self) -> None:
        self._records.clear()


class InMemoryAttributionAdjustmentRepository(AttributionAdjustmentRepository):
    def __init__(self):
        self._adjustments: Dict[str, AttributionAdjustment] = {}

    def save(self, adjustment: AttributionAdjustment) -> None:
        self._adjustments[adjustment.adjustment_id] = adjustment

    def find_by_original_id(self, original_id: str) -> List[AttributionAdjustment]:
        return [adj for adj in self._adjustments.values() if adj.original_attribution_id == original_id]

    def list_all(self) -> List[AttributionAdjustment]:
        return list(self._adjustments.values())

    def clear(self) -> None:
        self._adjustments.clear()


class FileAttributionRecordRepository(AttributionRecordRepository):
    def __init__(self, storage_dir: str = ".karsa/attribution/records/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, attr_id: str) -> str:
        return os.path.join(self.storage_dir, f"{attr_id}.json")

    def save(self, record: AttributionRecord) -> None:
        path = self._get_path(record.attribution_id)
        with open(path, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

    def find_by_attribution_id(self, attr_id: str) -> Optional[AttributionRecord]:
        path = self._get_path(attr_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return AttributionRecord.from_dict(data)

    def find_by_execution_id(self, exec_id: str) -> Optional[AttributionRecord]:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("execution_id") == exec_id:
                        return AttributionRecord.from_dict(data)
                except Exception:
                    pass
        return None

    def list_all(self) -> List[AttributionRecord]:
        records = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    records.append(AttributionRecord.from_dict(data))
                except Exception:
                    pass
        return records

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass


class FileAttributionAdjustmentRepository(AttributionAdjustmentRepository):
    def __init__(self, storage_dir: str = ".karsa/attribution/adjustments/"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, adjustment_id: str) -> str:
        return os.path.join(self.storage_dir, f"{adjustment_id}.json")

    def save(self, adjustment: AttributionAdjustment) -> None:
        path = self._get_path(adjustment.adjustment_id)
        with open(path, "w") as f:
            json.dump(adjustment.to_dict(), f, indent=2)

    def find_by_original_id(self, original_id: str) -> List[AttributionAdjustment]:
        adjustments = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("original_attribution_id") == original_id:
                        adjustments.append(AttributionAdjustment.from_dict(data))
                except Exception:
                    pass
        return adjustments

    def list_all(self) -> List[AttributionAdjustment]:
        adjustments = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    adjustments.append(AttributionAdjustment.from_dict(data))
                except Exception:
                    pass
        return adjustments

    def clear(self) -> None:
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.storage_dir, filename))
                except Exception:
                    pass
