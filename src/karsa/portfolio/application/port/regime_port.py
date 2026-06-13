import abc
from karsa.portfolio.domain.model.portfolio import RegimeState

class RegimePort(abc.ABC):
    @abc.abstractmethod
    def get_current_regime(self) -> RegimeState:
        pass
