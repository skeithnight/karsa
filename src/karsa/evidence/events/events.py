from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from karsa.shared.domain.event import DomainEvent

@dataclass
class EvidencePromotedEvent(DomainEvent):
    evidence_id: str = ""
    source_blob_id: str = ""
    provider_id: str = ""
    asset_id: str = ""
    payload_hash: str = ""
    extracted_at: Optional[datetime] = None
    promoted_at: Optional[datetime] = None
