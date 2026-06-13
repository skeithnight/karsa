import abc

class TreasuryPort(abc.ABC):
    @abc.abstractmethod
    def get_buying_power(self, portfolio_id: str) -> float:
        pass
