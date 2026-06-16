from karsa.performance_engine.domain.models import PerformanceEvaluation, RegimeDistribution
from datetime import datetime
from decimal import Decimal

class EvaluatePerformanceService:
    def __init__(self, repo, uow):
        self.repo = repo
        self.uow = uow
        
    def execute(self, eval_urn, outcome_urn, journal_urn, expected, actual, regime_dict):
        error = abs(Decimal(expected) - Decimal(actual))
        regime = RegimeDistribution(
            bull=Decimal(str(regime_dict.get('bull', 0))),
            bear=Decimal(str(regime_dict.get('bear', 0))),
            sideways=Decimal(str(regime_dict.get('sideways', 0)))
        )
        eval_obj = PerformanceEvaluation(eval_urn, outcome_urn, journal_urn, error, regime, datetime.utcnow())
        with self.uow:
            self.repo.save(eval_obj)
            self.uow.commit()
        return eval_obj
