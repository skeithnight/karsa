from typing import Optional, Dict
from karsa.thesis.domain.repository.thesis_repository import ThesisRepository
from karsa.thesis.domain.model.thesis import ActiveThesis
from karsa.thesis.infrastructure.storage.thesis_mapper import ThesisMapper
from karsa.thesis.infrastructure.storage.thesis_records import ThesisRecord

class InMemoryThesisRepository(ThesisRepository):
    def __init__(self):
        self._store: Dict[str, ThesisRecord] = {}

    def save(self, thesis: ActiveThesis) -> None:
        record = ThesisMapper.to_record(thesis)
        self._store[record.thesis_id] = record

    def get_by_id(self, thesis_id: str) -> Optional[ActiveThesis]:
        record = self._store.get(thesis_id)
        if not record:
            return None
        return ThesisMapper.to_domain(record)

    def exists(self, thesis_id: str) -> bool:
        return thesis_id in self._store

    def delete(self, thesis_id: str) -> None:
        if thesis_id in self._store:
            del self._store[thesis_id]
