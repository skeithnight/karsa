from dataclasses import dataclass, asdict
from typing import Dict, Any
import json

@dataclass(frozen=True)
class CapabilityJob:
    execution_id: str
    capability_urn_str: str
    workspace_id: str
    branch_id: str
    input_payload: Dict[str, Any]
    budget_dict: Dict[str, Any]

    def serialize(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def deserialize(cls, serialized_str: str) -> "CapabilityJob":
        data = json.loads(serialized_str)
        return cls(**data)
