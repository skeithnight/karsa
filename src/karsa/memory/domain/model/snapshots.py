from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class ArtifactProvenance:
    author: str
    reason: str

@dataclass
class ImmutableSnapshot:
    snapshot_id: str
    namespace: str
    payload_hash: str
    schema_id: str
    importance_tier: str
    created_at: datetime
    provenance: ArtifactProvenance

@dataclass
class ArtifactLineage:
    source_id: str
    target_id: str
    relationship_type: str  # e.g. "DERIVED_FROM", "SUPERSEDES"
    
@dataclass
class ArtifactSchema:
    schema_id: str
    version: str
    json_schema: Dict[str, Any]
    active: bool
