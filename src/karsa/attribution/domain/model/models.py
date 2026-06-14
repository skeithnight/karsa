from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict
from karsa.shared.domain.aggregate import VersionedAggregate

class AttributionSession(VersionedAggregate):
    VALID_STATES = {"STAGED", "COMPUTING", "CALIBRATED", "SEALED"}

    def __init__(
        self,
        session_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
        state: str = "STAGED",
        compounding_strategy: str = "FRONGELLO",
        raw_input_manifest_hash: str = "",
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.session_id = session_id
        self.horizon_start = horizon_start
        self.horizon_end = horizon_end
        self.state = state
        self.compounding_strategy = compounding_strategy
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
        if self.compounding_strategy not in {"FRONGELLO", "CARINO", "MENCHERO"}:
            raise ValueError(f"Invalid compounding strategy: {self.compounding_strategy}")

    def transition_to(self, new_state: str):
        if new_state not in self.VALID_STATES:
            raise ValueError(f"Invalid target state: {new_state}")

        # Check state transitions: STAGED -> COMPUTING -> CALIBRATED -> SEALED
        current = self.state
        if current == "STAGED" and new_state != "COMPUTING":
            raise ValueError(f"Cannot transition from STAGED to {new_state}")
        elif current == "COMPUTING" and new_state != "CALIBRATED" and new_state != "STAGED":
            # Allow fallback to STAGED on calculation failures
            raise ValueError(f"Cannot transition from COMPUTING to {new_state}")
        elif current == "CALIBRATED" and new_state != "SEALED" and new_state != "STAGED":
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
            "compounding_strategy": self.compounding_strategy,
            "raw_input_manifest_hash": self.raw_input_manifest_hash,
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AttributionSession':
        start = datetime.fromisoformat(data["horizon_start"]) if isinstance(data["horizon_start"], str) else data["horizon_start"]
        end = datetime.fromisoformat(data["horizon_end"]) if isinstance(data["horizon_end"], str) else data["horizon_end"]
        return cls(
            session_id=data["session_id"],
            horizon_start=start,
            horizon_end=end,
            state=data["state"],
            compounding_strategy=data.get("compounding_strategy", "FRONGELLO"),
            raw_input_manifest_hash=data.get("raw_input_manifest_hash", ""),
            aggregate_version=data.get("aggregate_version", 1)
        )


class PerformanceAttributionRecord(VersionedAggregate):
    def __init__(
        self,
        record_id: str,
        session_id: str,
        decision_id: str,
        thesis_urn: str,
        worker_urn: str,
        capability_urn: str,
        regime_urn: str,
        asset_urn: str,
        selection_return: Decimal,
        allocation_return: Decimal,
        execution_return: Decimal,
        beta_return: Decimal,
        liquidation_tracking_residual: Decimal = Decimal("0.0"),
        attribution_version: int = 1,
        is_active: bool = True,
        calculated_at: Optional[datetime] = None,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.record_id = record_id
        self.session_id = session_id
        self.decision_id = decision_id
        self.thesis_urn = thesis_urn
        self.worker_urn = worker_urn
        self.capability_urn = capability_urn
        self.regime_urn = regime_urn
        self.asset_urn = asset_urn
        self.selection_return = Decimal(str(selection_return))
        self.allocation_return = Decimal(str(allocation_return))
        self.execution_return = Decimal(str(execution_return))
        self.beta_return = Decimal(str(beta_return))
        self.liquidation_tracking_residual = Decimal(str(liquidation_tracking_residual))
        self.attribution_version = attribution_version
        self.is_active = is_active
        self.calculated_at = calculated_at or datetime.utcnow()
        self.validate()
        self._initialized = True

    def validate(self):
        if not self.record_id:
            raise ValueError("record_id is required")
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.thesis_urn:
            raise ValueError("thesis_urn is required")
        if not self.worker_urn:
            raise ValueError("worker_urn is required")
        if not self.capability_urn:
            raise ValueError("capability_urn is required")
        if not self.regime_urn:
            raise ValueError("regime_urn is required")
        if not self.asset_urn:
            raise ValueError("asset_urn is required")
        if self.attribution_version < 1:
            raise ValueError("attribution_version must be positive")

    def __setattr__(self, name, value):
        # Allow updating ONLY is_active flag after initialization
        if getattr(self, "_initialized", False):
            if name == "is_active":
                # Only allow toggling from True to False (superseding)
                if not value and self.is_active:
                    super().__setattr__(name, value)
                    self.increment_version()
                    return
                else:
                    raise TypeError("Cannot toggle is_active from False to True or re-apply same active status")
            elif name == "aggregate_version":
                super().__setattr__(name, value)
                return
            raise TypeError("Cannot modify immutable PerformanceAttributionRecord aggregate")
        super().__setattr__(name, value)

    def __delattr__(self, name):
        if getattr(self, "_initialized", False):
            raise TypeError("Cannot delete immutable PerformanceAttributionRecord properties")
        super().__delattr__(name)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "session_id": self.session_id,
            "decision_id": self.decision_id,
            "thesis_urn": self.thesis_urn,
            "worker_urn": self.worker_urn,
            "capability_urn": self.capability_urn,
            "regime_urn": self.regime_urn,
            "asset_urn": self.asset_urn,
            "selection_return": str(self.selection_return),
            "allocation_return": str(self.allocation_return),
            "execution_return": str(self.execution_return),
            "beta_return": str(self.beta_return),
            "liquidation_tracking_residual": str(self.liquidation_tracking_residual),
            "attribution_version": self.attribution_version,
            "is_active": self.is_active,
            "calculated_at": self.calculated_at.isoformat(),
            "aggregate_version": self.aggregate_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PerformanceAttributionRecord':
        calculated_at = datetime.fromisoformat(data["calculated_at"]) if isinstance(data["calculated_at"], str) else data["calculated_at"]
        return cls(
            record_id=data["record_id"],
            session_id=data["session_id"],
            decision_id=data["decision_id"],
            thesis_urn=data["thesis_urn"],
            worker_urn=data["worker_urn"],
            capability_urn=data["capability_urn"],
            regime_urn=data["regime_urn"],
            asset_urn=data["asset_urn"],
            selection_return=Decimal(data["selection_return"]),
            allocation_return=Decimal(data["allocation_return"]),
            execution_return=Decimal(data["execution_return"]),
            beta_return=Decimal(data["beta_return"]),
            liquidation_tracking_residual=Decimal(data.get("liquidation_tracking_residual", "0.0")),
            attribution_version=data["attribution_version"],
            is_active=data["is_active"],
            calculated_at=calculated_at,
            aggregate_version=data.get("aggregate_version", 1)
        )
