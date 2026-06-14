import json
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional

public_key_normalization = Decimal("0.000000000000")

class CompoundingStrategy(ABC):
    @abstractmethod
    def compound_returns(
        self,
        daily_returns: List[Dict[str, Any]],
        effects: List[Dict[str, Decimal]]
    ) -> Dict[str, Decimal]:
        """
        daily_returns: List of dicts with keys 'portfolio_return', 'benchmark_return' (each can be Decimal/float)
        effects: List of dicts with keys 'selection', 'allocation', 'execution', 'beta'
        """
        pass


class FrongelloCompounding(CompoundingStrategy):
    def compound_returns(
        self,
        daily_returns: List[Dict[str, Any]],
        effects: List[Dict[str, Decimal]]
    ) -> Dict[str, Decimal]:
        if not daily_returns:
            return {
                "selection": Decimal("0.0"),
                "allocation": Decimal("0.0"),
                "execution": Decimal("0.0"),
                "beta": Decimal("0.0"),
                "residual": Decimal("0.0")
            }

        T = len(daily_returns)
        # Apply safety floor to returns
        floor = Decimal("-0.999999")
        p_returns = []
        b_returns = []
        residuals = []

        for r in daily_returns:
            p_val = Decimal(str(r.get("portfolio_return", 0.0)))
            b_val = Decimal(str(r.get("benchmark_return", 0.0)))
            
            p_floored = max(p_val, floor)
            b_floored = max(b_val, floor)
            
            p_returns.append(p_floored)
            b_returns.append(b_floored)
            
            # Record residual between actual return and floored return
            res = (p_val - p_floored) - (b_val - b_floored)
            residuals.append(res)

        total_residual = sum(residuals)

        # Precompute compounding factors
        # cumulative portfolio returns up to day t-1
        cum_p = [Decimal("1.0")] * T
        for t in range(1, T):
            cum_p[t] = cum_p[t - 1] * (Decimal("1.0") + p_returns[t - 1])

        # cumulative benchmark returns after day t
        cum_b = [Decimal("1.0")] * T
        for t in range(T - 1, -1, -1):
            if t == T - 1:
                cum_b[t] = Decimal("1.0")
            else:
                cum_b[t] = cum_b[t + 1] * (Decimal("1.0") + b_returns[t + 1])

        smoothed_effects = {
            "selection": Decimal("0.0"),
            "allocation": Decimal("0.0"),
            "execution": Decimal("0.0"),
            "beta": Decimal("0.0")
        }

        for t in range(T):
            beta_t = cum_p[t] * cum_b[t]
            day_eff = effects[t]
            for key in ["selection", "allocation", "execution", "beta"]:
                val = Decimal(str(day_eff.get(key, 0.0)))
                smoothed_effects[key] += val * beta_t

        smoothed_effects["residual"] = total_residual
        return smoothed_effects


class CarinoCompounding(CompoundingStrategy):
    def compound_returns(
        self,
        daily_returns: List[Dict[str, Any]],
        effects: List[Dict[str, Decimal]]
    ) -> Dict[str, Decimal]:
        if not daily_returns:
            return {
                "selection": Decimal("0.0"),
                "allocation": Decimal("0.0"),
                "execution": Decimal("0.0"),
                "beta": Decimal("0.0"),
                "residual": Decimal("0.0")
            }

        T = len(daily_returns)
        p_returns = [Decimal(str(r.get("portfolio_return", 0.0))) for r in daily_returns]
        b_returns = [Decimal(str(r.get("benchmark_return", 0.0))) for r in daily_returns]

        # Calculate multi-period compounding return
        prod_p = Decimal("1.0")
        prod_b = Decimal("1.0")
        for t in range(T):
            prod_p *= (Decimal("1.0") + p_returns[t])
            prod_b *= (Decimal("1.0") + b_returns[t])

        R_p = prod_p - Decimal("1.0")
        R_b = prod_b - Decimal("1.0")

        # Logarithmic smoothing factor for total period
        if R_p == R_b:
            K = Decimal("1.0") / (Decimal("1.0") + R_p)
        else:
            if (Decimal("1.0") + R_p) <= 0 or (Decimal("1.0") + R_b) <= 0:
                raise ValueError("Logarithm of non-positive return value in Carino compounding. Use Frongello.")
            K = (Decimal(str(math.log(float(Decimal("1.0") + R_p)))) - Decimal(str(math.log(float(Decimal("1.0") + R_b))))) / (R_p - R_b)

        smoothed_effects = {
            "selection": Decimal("0.0"),
            "allocation": Decimal("0.0"),
            "execution": Decimal("0.0"),
            "beta": Decimal("0.0"),
            "residual": Decimal("0.0")
        }

        for t in range(T):
            rp = p_returns[t]
            rb = b_returns[t]
            if rp == rb:
                k_t = Decimal("1.0") / (Decimal("1.0") + rp)
            else:
                if (Decimal("1.0") + rp) <= 0 or (Decimal("1.0") + rb) <= 0:
                    raise ValueError("Logarithm of non-positive daily return in Carino compounding.")
                k_t = (Decimal(str(math.log(float(Decimal("1.0") + rp)))) - Decimal(str(math.log(float(Decimal("1.0") + rb))))) / (rp - rb)

            w_t = k_t / K if K != 0 else Decimal("1.0")
            day_eff = effects[t]
            for key in ["selection", "allocation", "execution", "beta"]:
                val = Decimal(str(day_eff.get(key, 0.0)))
                smoothed_effects[key] += val * w_t

        return smoothed_effects


class MencheroCompounding(CompoundingStrategy):
    def compound_returns(
        self,
        daily_returns: List[Dict[str, Any]],
        effects: List[Dict[str, Decimal]]
    ) -> Dict[str, Decimal]:
        if not daily_returns:
            return {
                "selection": Decimal("0.0"),
                "allocation": Decimal("0.0"),
                "execution": Decimal("0.0"),
                "beta": Decimal("0.0"),
                "residual": Decimal("0.0")
            }

        T = len(daily_returns)
        p_returns = [Decimal(str(r.get("portfolio_return", 0.0))) for r in daily_returns]
        b_returns = [Decimal(str(r.get("benchmark_return", 0.0))) for r in daily_returns]

        prod_p = Decimal("1.0")
        prod_b = Decimal("1.0")
        for t in range(T):
            prod_p *= (Decimal("1.0") + p_returns[t])
            prod_b *= (Decimal("1.0") + b_returns[t])

        R_p = prod_p - Decimal("1.0")
        R_b = prod_b - Decimal("1.0")

        excess_sum = sum(p_returns[t] - b_returns[t] for t in range(T))
        if excess_sum == 0:
            theta = Decimal("1.0")
        else:
            theta = (R_p - R_b) / excess_sum

        smoothed_effects = {
            "selection": Decimal("0.0"),
            "allocation": Decimal("0.0"),
            "execution": Decimal("0.0"),
            "beta": Decimal("0.0"),
            "residual": Decimal("0.0")
        }

        for t in range(T):
            day_eff = effects[t]
            for key in ["selection", "allocation", "execution", "beta"]:
                val = Decimal(str(day_eff.get(key, 0.0)))
                smoothed_effects[key] += val * theta

        return smoothed_effects


class CanonicalManifestSerializer:
    @staticmethod
    def _normalize_val(val: Any) -> Any:
        if isinstance(val, (Decimal, float)):
            # Normalize to string with 12 decimal places
            d = Decimal(str(val))
            # Round half up to avoid floating point representations
            rounded = d.quantize(Decimal("1e-12"), rounding=ROUND_HALF_UP)
            return f"{rounded:f}"
        elif isinstance(val, datetime):
            # Normalize to UTC string
            return val.astimezone(datetime.now(timezone.utc).tzinfo).strftime("%Y-%m-%dT%H:%M:%S.000000Z") if val.tzinfo else val.strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        elif isinstance(val, date):
            return val.strftime("%Y-%m-%d")
        elif isinstance(val, dict):
            # Recursively normalize
            cleaned = {}
            for k, v in val.items():
                if v is not None:
                    cleaned[k] = CanonicalManifestSerializer._normalize_val(v)
            # Sort keys lexicographically
            return {k: cleaned[k] for k in sorted(cleaned.keys())}
        elif isinstance(val, list):
            # Normalize components
            normalized_list = [CanonicalManifestSerializer._normalize_val(x) for x in val if x is not None]
            # Deterministic sorting if items are dicts with URN or id, otherwise sort string representation
            def sort_key(item):
                if isinstance(item, dict):
                    for key in ["asset_urn", "execution_id", "decision_id", "record_id", "session_id"]:
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
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BenchmarkSnapshot:
    snapshot_urn: str
    benchmark_urn: str
    start_date: str
    end_date: str
    daily_returns: Dict[str, str]  # string representation of Decimals
    manifest_hash: str

    def get_returns_dict(self) -> Dict[str, Decimal]:
        return {k: Decimal(v) for k, v in self.daily_returns.items()}
