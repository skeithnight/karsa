from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timezone
from typing import List, Optional, Any
import json

@dataclass(frozen=True)
class BrierScore:
    score_value: Decimal

@dataclass(frozen=True)
class CalibrationBin:
    bin_range_start: Decimal            # e.g., 0.80
    bin_range_end: Decimal              # e.g., 0.90
    prediction_count: int
    success_count: int
    calibrated_probability: Decimal     # success_count / prediction_count

@dataclass(frozen=True)
class CalibrationCurve:
    bins: List[CalibrationBin]

@dataclass(frozen=True)
class BenchmarkPerformance:
    benchmark_name: str                 # e.g., "SPY", "QQQ"
    excess_return: Decimal
    drawdown_pct: Decimal
    index_snapshot_value: Decimal       # Frozen price at evaluation time

@dataclass(frozen=True)
class WorkerRank:
    worker_urn: str
    rank_index: int
    brier_score_ema: Decimal
    drawdown_ema: Decimal


class CanonicalManifestSerializer:
    @staticmethod
    def _normalize_val(val: Any) -> Any:
        if isinstance(val, (Decimal, float)):
            d = Decimal(str(val))
            rounded = d.quantize(Decimal("1e-12"), rounding=ROUND_HALF_UP)
            return f"{rounded:f}"
        elif isinstance(val, datetime):
            return val.astimezone(datetime.now(timezone.utc).tzinfo).strftime("%Y-%m-%dT%H:%M:%S.000000Z") if val.tzinfo else val.strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        elif isinstance(val, date):
            return val.strftime("%Y-%m-%d")
        elif isinstance(val, dict):
            cleaned = {}
            for k, v in val.items():
                if v is not None:
                    cleaned[k] = CanonicalManifestSerializer._normalize_val(v)
            return {k: cleaned[k] for k in sorted(cleaned.keys())}
        elif isinstance(val, list):
            normalized_list = [CanonicalManifestSerializer._normalize_val(x) for x in val if x is not None]
            def sort_key(item):
                if isinstance(item, dict):
                    for key in ["asset_urn", "execution_id", "decision_id", "record_id", "session_id", "worker_urn"]:
                        if key in item:
                            return str(item[key])
                return str(item)
            return sorted(normalized_list, key=sort_key)
        else:
            return val

    @classmethod
    def serialize(cls, manifest_dict: dict) -> str:
        normalized = cls._normalize_val(manifest_dict)
        return json.dumps(normalized, sort_keys=True, separators=(',', ':'))

    @classmethod
    def generate_hash(cls, manifest_dict: dict) -> str:
        import hashlib
        serialized = cls.serialize(manifest_dict)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class EvaluationTarget:
    target_type: str
    target_id: str


@dataclass(frozen=True)
class EvaluationPeriod:
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class ThesisQualityMetric:
    brier_score: Decimal
    is_invalidated: bool
    parameter_deviation: Decimal


@dataclass(frozen=True)
class ExecutionQualityMetric:
    slippage_bps: Decimal
    fill_latency_ms: int
    token_count: int


@dataclass(frozen=True)
class AllocationQualityMetric:
    sharpe_ratio: Decimal
    drawdown_pct: Decimal
    excess_return_bps: Decimal


@dataclass(frozen=True)
class BenchmarkComparison:
    benchmark_name: str
    excess_return: Decimal
    drawdown_pct: Decimal
    index_snapshot_value: Decimal
