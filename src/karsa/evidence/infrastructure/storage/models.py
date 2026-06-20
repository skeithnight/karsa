from sqlalchemy import Column, String, JSON, DateTime
from karsa.shared.persistence.base import Base
from karsa.shared.persistence.mixins import UUIDMixin

class PromotedEvidenceModel(UUIDMixin, Base):
    __tablename__ = 'promoted_evidence'
    
    evidence_id = Column(String(255), unique=True, nullable=False, index=True)
    source_blob_id = Column(String(255), nullable=False, index=True)
    provider_id = Column(String(255), nullable=False)
    asset_id = Column(String(255), nullable=False, index=True)
    payload_hash = Column(String(64), unique=True, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    extracted_at = Column(DateTime(timezone=True), nullable=False)
    promoted_at = Column(DateTime(timezone=True), nullable=False)
