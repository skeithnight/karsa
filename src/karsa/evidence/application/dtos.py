from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class EvidencePromotionRequestDTO:
    source_blob_id: str
    provider_id: str
    asset_id: str
    extracted_at: datetime
    payload: Dict[str, Any]

@dataclass
class EvidenceResponseDTO:
    evidence_id: str
    source_blob_id: str
    provider_id: str
    asset_id: str
    payload_hash: str
    payload: Dict[str, Any]
    extracted_at: datetime
    promoted_at: datetime
    evidence_urn: str
