from typing import Optional, List
from sqlalchemy.orm import Session
from karsa.evidence.domain.models import PromotedEvidence
from karsa.evidence.infrastructure.storage.models import PromotedEvidenceModel

class EvidenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, evidence: PromotedEvidence):
        em = PromotedEvidenceModel(
            evidence_id=evidence.evidence_id,
            source_blob_id=evidence.source_blob_id,
            provider_id=evidence.provider_id,
            asset_id=evidence.asset_id,
            payload_hash=evidence.payload_hash,
            payload=evidence.payload,
            extracted_at=evidence.extracted_at,
            promoted_at=evidence.promoted_at
        )
        self.session.add(em)

    def get(self, evidence_id: str) -> Optional[PromotedEvidence]:
        em = self.session.query(PromotedEvidenceModel).filter_by(evidence_id=evidence_id).first()
        if not em:
            return None
        ev = PromotedEvidence(
            source_blob_id=em.source_blob_id,
            provider_id=em.provider_id,
            asset_id=em.asset_id,
            extracted_at=em.extracted_at,
            payload=em.payload
        )
        # Override generated fields
        ev.evidence_id = em.evidence_id
        ev.aggregate_id = em.evidence_id
        ev.payload_hash = em.payload_hash
        ev.promoted_at = em.promoted_at
        ev._domain_events.clear() # Clear events generated during object rehydration
        return ev
        
    def get_by_hash(self, payload_hash: str) -> Optional[PromotedEvidence]:
        em = self.session.query(PromotedEvidenceModel).filter_by(payload_hash=payload_hash).first()
        if not em:
            return None
        return self.get(em.evidence_id)
