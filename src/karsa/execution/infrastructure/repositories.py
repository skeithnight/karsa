import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from karsa.execution.domain.exceptions import DatabaseImmutabilityError
from karsa.execution.domain.models import (
    ExecutionRequest, RoutingRecord, FillRecord, PEPValidationStatus, RouteStatus
)


# ----------------- Serialization & Deserialization Helpers -----------------

def serialize_execution_request(req: ExecutionRequest) -> Dict[str, Any]:
    return {
        "execution_id": req.execution_id,
        "correlation_id": req.correlation_id,
        "causation_id": req.causation_id,
        "symbol": req.symbol,
        "quantity": req.quantity,
        "direction": req.direction,
        "order_type": req.order_type,
        "price": req.price,
        "cio_signature": req.cio_signature,
        "gov_exception_id": req.gov_exception_id,
        "gov_exception_signature": req.gov_exception_signature,
        "pep_status": req.pep_status.value,
        "rejection_reason": req.rejection_reason,
        "created_at": req.created_at,
    }


def deserialize_execution_request(data: Dict[str, Any]) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=data["execution_id"],
        correlation_id=data["correlation_id"],
        causation_id=data["causation_id"],
        symbol=data["symbol"],
        quantity=data["quantity"],
        direction=data["direction"],
        order_type=data["order_type"],
        price=data["price"],
        cio_signature=data["cio_signature"],
        gov_exception_id=data.get("gov_exception_id"),
        gov_exception_signature=data.get("gov_exception_signature"),
        pep_status=PEPValidationStatus(data["pep_status"]),
        rejection_reason=data.get("rejection_reason"),
        created_at=data["created_at"],
    )


def serialize_routing_record(record: RoutingRecord) -> Dict[str, Any]:
    return {
        "route_id": record.route_id,
        "execution_id": record.execution_id,
        "broker_id": record.broker_id,
        "broker_order_ref": record.broker_order_ref,
        "route_status": record.route_status.value,
        "created_at": record.created_at,
    }


def deserialize_routing_record(data: Dict[str, Any]) -> RoutingRecord:
    return RoutingRecord(
        route_id=data["route_id"],
        execution_id=data["execution_id"],
        broker_id=data["broker_id"],
        broker_order_ref=data.get("broker_order_ref"),
        route_status=RouteStatus(data["route_status"]),
        created_at=data["created_at"],
    )


def serialize_fill_record(record: FillRecord) -> Dict[str, Any]:
    return {
        "fill_id": record.fill_id,
        "route_id": record.route_id,
        "filled_quantity": record.filled_quantity,
        "filled_price": record.filled_price,
        "commission": record.commission,
        "slippage": record.slippage,
        "created_at": record.created_at,
    }


def deserialize_fill_record(data: Dict[str, Any]) -> FillRecord:
    return FillRecord(
        fill_id=data["fill_id"],
        route_id=data["route_id"],
        filled_quantity=data["filled_quantity"],
        filled_price=data["filled_price"],
        commission=data["commission"],
        slippage=data["slippage"],
        created_at=data["created_at"],
    )


# ----------------- InMemory Repositories -----------------

class InMemoryExecutionRequestRepository:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def append(self, request: ExecutionRequest) -> None:
        if request.execution_id in self._data:
            raise DatabaseImmutabilityError(
                f"Ledger record {request.execution_id} already exists. Updates/Deletes are prohibited."
            )
        self._data[request.execution_id] = serialize_execution_request(request)

    def find_by_id(self, execution_id: str) -> Optional[ExecutionRequest]:
        data = self._data.get(execution_id)
        if not data:
            return None
        return deserialize_execution_request(data)


class InMemoryRoutingRecordRepository:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def append(self, record: RoutingRecord) -> None:
        if record.route_id in self._data:
            raise DatabaseImmutabilityError(
                f"Ledger record {record.route_id} already exists. Updates/Deletes are prohibited."
            )
        self._data[record.route_id] = serialize_routing_record(record)

    def find_by_id(self, route_id: str) -> Optional[RoutingRecord]:
        data = self._data.get(route_id)
        if not data:
            return None
        return deserialize_routing_record(data)

    def find_by_execution_id(self, execution_id: str) -> List[RoutingRecord]:
        results = []
        for data in self._data.values():
            if data["execution_id"] == execution_id:
                results.append(deserialize_routing_record(data))
        return results


class InMemoryFillRecordRepository:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def append(self, record: FillRecord) -> None:
        if record.fill_id in self._data:
            raise DatabaseImmutabilityError(
                f"Ledger record {record.fill_id} already exists. Updates/Deletes are prohibited."
            )
        self._data[record.fill_id] = serialize_fill_record(record)

    def find_by_id(self, fill_id: str) -> Optional[FillRecord]:
        data = self._data.get(fill_id)
        if not data:
            return None
        return deserialize_fill_record(data)

    def find_by_route_id(self, route_id: str) -> List[FillRecord]:
        results = []
        for data in self._data.values():
            if data["route_id"] == route_id:
                results.append(deserialize_fill_record(data))
        return results


# ----------------- File Repositories -----------------

class FileExecutionRequestRepository:
    def __init__(self, workspace_path: Optional[Path] = None) -> None:
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "execution" / "requests"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, execution_id: str) -> Path:
        # Sanitize URN path separators for files
        filename = execution_id.replace(":", "_")
        return self.base_dir / f"{filename}.json"

    def append(self, request: ExecutionRequest) -> None:
        path = self._get_path(request.execution_id)
        if path.exists():
            raise DatabaseImmutabilityError(
                f"Ledger record {request.execution_id} already exists. Updates/Deletes are prohibited."
            )
        serialized_data = serialize_execution_request(request)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, execution_id: str) -> Optional[ExecutionRequest]:
        path = self._get_path(execution_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_execution_request(data)
        except Exception:
            return None


class FileRoutingRecordRepository:
    def __init__(self, workspace_path: Optional[Path] = None) -> None:
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "execution" / "routes"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, route_id: str) -> Path:
        filename = route_id.replace(":", "_")
        return self.base_dir / f"{filename}.json"

    def append(self, record: RoutingRecord) -> None:
        path = self._get_path(record.route_id)
        if path.exists():
            raise DatabaseImmutabilityError(
                f"Ledger record {record.route_id} already exists. Updates/Deletes are prohibited."
            )
        serialized_data = serialize_routing_record(record)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, route_id: str) -> Optional[RoutingRecord]:
        path = self._get_path(route_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_routing_record(data)
        except Exception:
            return None

    def find_by_execution_id(self, execution_id: str) -> List[RoutingRecord]:
        results = []
        if not self.base_dir.exists():
            return results
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("execution_id") == execution_id:
                        results.append(deserialize_routing_record(data))
                except Exception:
                    pass
        return results


class FileFillRecordRepository:
    def __init__(self, workspace_path: Optional[Path] = None) -> None:
        self.base_dir = Path(workspace_path or ".").resolve() / ".karsa" / "execution" / "fills"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, fill_id: str) -> Path:
        filename = fill_id.replace(":", "_")
        return self.base_dir / f"{filename}.json"

    def append(self, record: FillRecord) -> None:
        path = self._get_path(record.fill_id)
        if path.exists():
            raise DatabaseImmutabilityError(
                f"Ledger record {record.fill_id} already exists. Updates/Deletes are prohibited."
            )
        serialized_data = serialize_fill_record(record)
        with open(path, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def find_by_id(self, fill_id: str) -> Optional[FillRecord]:
        path = self._get_path(fill_id)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return deserialize_fill_record(data)
        except Exception:
            return None

    def find_by_route_id(self, route_id: str) -> List[FillRecord]:
        results = []
        if not self.base_dir.exists():
            return results
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                path = self.base_dir / filename
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    if data.get("route_id") == route_id:
                        results.append(deserialize_fill_record(data))
                except Exception:
                    pass
        return results
