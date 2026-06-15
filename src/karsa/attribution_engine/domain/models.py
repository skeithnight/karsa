from dataclasses import dataclass
from typing import Dict
from decimal import Decimal

@dataclass(frozen=True)
class FactorModelVersion:
    version_urn: str
    model_hash: str

@dataclass(frozen=True)
class AttributionDecomposition:
    attrib_urn: str
    eval_urn: str
    factor_model_version_urn: str
    causal_fractions: Dict[str, Decimal]
