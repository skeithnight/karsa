import abc
from typing import Optional
from karsa.thesis.domain.model.thesis import ActiveThesis

class ThesisRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, thesis: ActiveThesis) -> None:
        pass
        
    @abc.abstractmethod
    def get_by_id(self, thesis_id: str) -> Optional[ActiveThesis]:
        pass
        
    @abc.abstractmethod
    def exists(self, thesis_id: str) -> bool:
        pass
        
    @abc.abstractmethod
    def delete(self, thesis_id: str) -> None:
        pass
