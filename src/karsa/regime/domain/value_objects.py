from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json

@dataclass(frozen=True)
class SignalConfidenceScore:
    value: Decimal

    def __post_init__(self):
        if not (Decimal('0.0') <= self.value <= Decimal('1.0')):
            raise ValueError("SignalConfidenceScore must be between 0.0 and 1.0")

    def __repr__(self) -> str:
        return f"SignalConfidenceScore({self.value})"

    @staticmethod
    def canonical_meaning() -> str:
        return "Weighted Signal Confidence"

    @staticmethod
    def prohibited_interpretations() -> list[str]:
        return [
            "probability",
            "expected return",
            "win rate",
            "forecast accuracy"
        ]

    def to_dict(self) -> dict:
        return {"value": str(self.value)}

@dataclass(frozen=True)
class RegimeEvidence:
    evidence_type: str
    evidence_value: Decimal
    evidence_weight: Decimal
    evidence_contribution: Decimal
    evidence_methodology_urn: str
    evidence_policy_hash: str
    evidence_manifest_hash: str

    def to_dict(self) -> dict:
        return {
            "evidence_type": self.evidence_type,
            "evidence_value": str(self.evidence_value),
            "evidence_weight": str(self.evidence_weight),
            "evidence_contribution": str(self.evidence_contribution),
            "evidence_methodology_urn": self.evidence_methodology_urn,
            "evidence_policy_hash": self.evidence_policy_hash,
            "evidence_manifest_hash": self.evidence_manifest_hash
        }

@dataclass(frozen=True)
class RegimeHorizon:
    horizon_urn: str
    days: int

    def to_dict(self) -> dict:
        return {
            "horizon_urn": self.horizon_urn,
            "days": self.days
        }

@dataclass(frozen=True)
class RegimeClassification:
    market_regime: str
    volatility_regime: str
    liquidity_regime: str

    def to_dict(self) -> dict:
        return {
            "market_regime": self.market_regime,
            "volatility_regime": self.volatility_regime,
            "liquidity_regime": self.liquidity_regime
        }

@dataclass(frozen=True)
class RegimeMethodologyManifest:
    regime_methodology_urn: str
    regime_policy_hash: str
    regime_strategy_version: str
    regime_manifest_hash: str

    def to_dict(self) -> dict:
        return {
            "regime_methodology_urn": self.regime_methodology_urn,
            "regime_policy_hash": self.regime_policy_hash,
            "regime_strategy_version": self.regime_strategy_version,
            "regime_manifest_hash": self.regime_manifest_hash
        }

    @classmethod
    def create(cls, regime_methodology_urn: str, regime_policy_hash: str, regime_strategy_version: str, evidence_manifest_hashes: list[str]) -> 'RegimeMethodologyManifest':
        data = {
            "regime_methodology_urn": regime_methodology_urn,
            "regime_policy_hash": regime_policy_hash,
            "regime_strategy_version": regime_strategy_version,
            "evidence_manifest_hashes": sorted(evidence_manifest_hashes)
        }
        canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True)
        manifest_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        return cls(
            regime_methodology_urn=regime_methodology_urn,
            regime_policy_hash=regime_policy_hash,
            regime_strategy_version=regime_strategy_version,
            regime_manifest_hash=manifest_hash
        )
