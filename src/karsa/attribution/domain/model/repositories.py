from abc import ABC, abstractmethod
from typing import Optional, List
from karsa.attribution.domain.model.models import AttributionRecord, AttributionAdjustment

class AttributionRecordRepository(ABC):
    @abstractmethod
    def save(self, record: AttributionRecord) -> None:
        pass

    @abstractmethod
    def find_by_attribution_id(self, attr_id: str) -> Optional[AttributionRecord]:
        pass

    @abstractmethod
    def find_by_execution_id(self, exec_id: str) -> Optional[AttributionRecord]:
        pass

    @abstractmethod
    def list_all(self) -> List[AttributionRecord]:
        pass


class AttributionAdjustmentRepository(ABC):
    @abstractmethod
    def save(self, adjustment: AttributionAdjustment) -> None:
        pass

    @abstractmethod
    def find_by_original_id(self, original_id: str) -> List[AttributionAdjustment]:
        pass

    @abstractmethod
    def list_all(self) -> List[AttributionAdjustment]:
        pass
