from abc import ABC, abstractmethod
from typing import Optional
from karsa.performance.domain.model.profile import PerformanceProfileWindow
from karsa.performance.domain.model.value_objects import TargetIdentity, WindowIdentity, PredictionMetrics, InvestmentMetrics
from karsa.shared.infrastructure.uow import ConcurrencyConflictError
import json

class ProfileRepository(ABC):
    @abstractmethod
    def get_by_identity(self, target: TargetIdentity, window: WindowIdentity) -> Optional[PerformanceProfileWindow]:
        pass

    @abstractmethod
    def save(self, profile: PerformanceProfileWindow) -> None:
        pass

class PostgresProfileRepository(ProfileRepository):
    def __init__(self, connection):
        self.connection = connection

    def get_by_identity(self, target: TargetIdentity, window: WindowIdentity) -> Optional[PerformanceProfileWindow]:
        cur = self.connection.cursor()
        cur.execute(
            "SELECT version, metrics FROM performance_profile_window WHERE target_id=%s AND target_type=%s AND window_value=%s",
            (target.target_id, target.target_type, window.period_value)
        )
        row = cur.fetchone()
        if not row:
            return None
        version = row[0]
        metrics = row[1] if isinstance(row[1], dict) else json.loads(row[1])
        return PerformanceProfileWindow(
            target_identity=target,
            window_identity=window,
            prediction_metrics=PredictionMetrics(**metrics.get('prediction_metrics', {})),
            investment_metrics=InvestmentMetrics(**metrics.get('investment_metrics', {})),
            version=version
        )

    def save(self, profile: PerformanceProfileWindow) -> None:
        cur = self.connection.cursor()
        metrics = {
            "prediction_metrics": profile.prediction_metrics.__dict__,
            "investment_metrics": profile.investment_metrics.__dict__
        }
        if profile.aggregate_version == 1:
            cur.execute(
                "INSERT INTO performance_profile_window (target_id, target_type, window_value, version, metrics, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (profile.target_identity.target_id, profile.target_identity.target_type, profile.window_identity.period_value, profile.aggregate_version, json.dumps(metrics))
            )
        else:
            cur.execute(
                "UPDATE performance_profile_window SET metrics=%s, version=%s, updated_at=CURRENT_TIMESTAMP WHERE target_id=%s AND target_type=%s AND window_value=%s AND version=%s",
                (json.dumps(metrics), profile.aggregate_version, profile.target_identity.target_id, profile.target_identity.target_type, profile.window_identity.period_value, profile.aggregate_version - 1)
            )
            if cur.rowcount == 0:
                raise ConcurrencyConflictError("OCC failure in PerformanceProfileWindow")
