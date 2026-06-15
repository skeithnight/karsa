from decimal import Decimal
from datetime import datetime
from typing import Optional
from karsa.shared.domain.aggregate import VersionedAggregate

class PerformanceSession(VersionedAggregate):
    VALID_STATES = {"STAGED", "EVALUATING", "CALIBRATED", "SEALED"}

    def __init__(
        self,
        session_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
        state: str = "STAGED",
        raw_input_manifest_hash: str = "",
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.session_id = session_id
        self.horizon_start = horizon_start
        self.horizon_end = horizon_end
        self.state = state
        self.raw_input_manifest_hash = raw_input_manifest_hash
        self.validate()

    def validate(self):
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.horizon_start or not isinstance(self.horizon_start, datetime):
            raise ValueError("horizon_start must be a datetime")
        if not self.horizon_end or not isinstance(self.horizon_end, datetime):
            raise ValueError("horizon_end must be a datetime")
        if self.horizon_start > self.horizon_end:
            raise ValueError("horizon_start cannot be after horizon_end")
        if self.state not in self.VALID_STATES:
            raise ValueError(f"Invalid state: {self.state}")

    def transition_to(self, new_state: str):
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid target state: {new_state}")

        current = self.state
        if current == "STAGED" and new_state != "EVALUATING":
            raise ValueError(f"Cannot transition from STAGED to {new_state}")
        elif current == "EVALUATING" and new_state not in {"CALIBRATED", "STAGED"}:
            raise ValueError(f"Cannot transition from EVALUATING to {new_state}")
        elif current == "CALIBRATED" and new_state not in {"SEALED", "STAGED"}:
            raise ValueError(f"Cannot transition from CALIBRATED to {new_state}")
        elif current == "SEALED":
            raise ValueError("Cannot transition out of SEALED state")

        self.state = new_state
        self.increment_version()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "horizon_start": self.horizon_start.isoformat(),
            "horizon_end": self.horizon_end.isoformat(),
            "state": self.state,
            "raw_input_manifest_hash": self.raw_input_manifest_hash,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PerformanceSession':
        start = datetime.fromisoformat(data["horizon_start"]) if isinstance(data["horizon_start"], str) else data["horizon_start"]
        end = datetime.fromisoformat(data["horizon_end"]) if isinstance(data["horizon_end"], str) else data["horizon_end"]
        return cls(
            session_id=data["session_id"],
            horizon_start=start,
            horizon_end=end,
            state=data["state"],
            raw_input_manifest_hash=data.get("raw_input_manifest_hash", ""),
            aggregate_version=data.get("aggregate_version", 1)
        )


class WorkerEvaluationRecord(VersionedAggregate):
    def __init__(
        self,
        record_id: str,
        session_id: str,
        decision_id: str,
        worker_urn: str,
        asset_urn: str,
        regime_urn: str,
        forecast_probability: Decimal,
        realized_outcome: int,
        brier_score_component: Decimal,
        realized_return: Decimal,
        evaluation_version: int = 1,
        is_active: bool = True,
        calculated_at: Optional[datetime] = None,
        superseded_by_version: Optional[int] = None,
        invalidated_by_version: Optional[int] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.record_id = record_id
        self.session_id = session_id
        self.decision_id = decision_id
        self.worker_urn = worker_urn
        self.asset_urn = asset_urn
        self.regime_urn = regime_urn
        self.forecast_probability = Decimal(str(forecast_probability))
        self.realized_outcome = realized_outcome
        self.brier_score_component = Decimal(str(brier_score_component))
        self.realized_return = Decimal(str(realized_return))
        self.evaluation_version = evaluation_version
        self.is_active = is_active
        self.calculated_at = calculated_at or datetime.utcnow()
        self.superseded_by_version = superseded_by_version
        self.invalidated_by_version = invalidated_by_version
        self.validate()
        self._initialized = True

    def validate(self):
        if not self.record_id:
            raise ValueError("record_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.worker_urn:
            raise ValueError("worker_urn is required")
        if not self.asset_urn:
            raise ValueError("asset_urn is required")
        if not self.regime_urn:
            raise ValueError("regime_urn is required")
        if self.forecast_probability < Decimal("0.0") or self.forecast_probability > Decimal("1.0"):
            raise ValueError("forecast_probability must be between 0.0 and 1.0")
        if self.realized_outcome not in {0, 1}:
            raise ValueError("realized_outcome must be 0 or 1")
        if self.evaluation_version < 1:
            raise ValueError("evaluation_version must be positive")

    def __setattr__(self, name, value):
        if getattr(self, "_initialized", False):
            if name == "is_active":
                if not value and self.is_active:
                    super().__setattr__(name, value)
                    self.increment_version()
                    return
                else:
                    raise TypeError("Cannot toggle is_active from False to True or re-apply same active status")
            elif name in ("superseded_by_version", "invalidated_by_version"):
                super().__setattr__(name, value)
                self.increment_version()
                return
            elif name == "aggregate_version":
                super().__setattr__(name, value)
                return
            raise TypeError("Cannot modify immutable WorkerEvaluationRecord aggregate")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot delete immutable WorkerEvaluationRecord properties")
        super().__delattr__(name)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "session_id": self.session_id,
            "decision_id": self.decision_id,
            "worker_urn": self.worker_urn,
            "asset_urn": self.asset_urn,
            "regime_urn": self.regime_urn,
            "forecast_probability": str(self.forecast_probability),
            "realized_outcome": self.realized_outcome,
            "brier_score_component": str(self.brier_score_component),
            "realized_return": str(self.realized_return),
            "evaluation_version": self.evaluation_version,
            "is_active": self.is_active,
            "calculated_at": self.calculated_at.isoformat(),
            "superseded_by_version": self.superseded_by_version,
            "invalidated_by_version": self.invalidated_by_version,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkerEvaluationRecord':
        calculated_at = datetime.fromisoformat(data["calculated_at"]) if isinstance(data["calculated_at"], str) else data["calculated_at"]
        return cls(
            record_id=data["record_id"],
            session_id=data["session_id"],
            decision_id=data["decision_id"],
            worker_urn=data["worker_urn"],
            asset_urn=data["asset_urn"],
            regime_urn=data["regime_urn"],
            forecast_probability=Decimal(data["forecast_probability"]),
            realized_outcome=data["realized_outcome"],
            brier_score_component=Decimal(data["brier_score_component"]),
            realized_return=Decimal(data["realized_return"]),
            evaluation_version=data["evaluation_version"],
            is_active=data["is_active"],
            calculated_at=calculated_at,
            superseded_by_version=data.get("superseded_by_version"),
            invalidated_by_version=data.get("invalidated_by_version"),
            aggregate_version=data.get("aggregate_version", 1)
        )
