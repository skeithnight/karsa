from typing import Optional
from karsa.evidence.domain.models import PromotedEvidence
from karsa.evidence.application.dtos import EvidencePromotionRequestDTO, EvidenceResponseDTO
from karsa.shared.identity.urn_builder import URNBuilder

class EvidencePromotionService:
    def __init__(self, repository, uow):
        self.repository = repository
        self.uow = uow

    def _to_dto(self, evidence: PromotedEvidence) -> EvidenceResponseDTO:
        urn = URNBuilder.build_evidence_urn(
            category=evidence.provider_id,
            date=evidence.extracted_at.strftime("%Y%m%d%H%M%S"),
            payload_hash=evidence.payload_hash[:8]
        )
        return EvidenceResponseDTO(
            evidence_id=evidence.evidence_id,
            source_blob_id=evidence.source_blob_id,
            provider_id=evidence.provider_id,
            asset_id=evidence.asset_id,
            payload_hash=evidence.payload_hash,
            payload=evidence.payload,
            extracted_at=evidence.extracted_at,
            promoted_at=evidence.promoted_at,
            evidence_urn=str(urn)
        )

    def promote_evidence(self, request: EvidencePromotionRequestDTO) -> EvidenceResponseDTO:
        # Check if identical payload was already promoted
        import hashlib
        import json
        payload_str = json.dumps(request.payload, sort_keys=True)
        phash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        existing = self.repository.get_by_hash(phash)
        if existing:
            return self._to_dto(existing)
            
        evidence = PromotedEvidence(
            source_blob_id=request.source_blob_id,
            provider_id=request.provider_id,
            asset_id=request.asset_id,
            extracted_at=request.extracted_at,
            payload=request.payload
        )
        
        try:
            with self.uow:
                self.repository.add(evidence)
                self.uow.commit()
        except Exception as e:
            # Check if this was a duplicate insertion race condition
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                self.uow.rollback()
                existing = self.repository.get_by_hash(phash)
                if existing:
                    return self._to_dto(existing)
            raise e
            
        return self._to_dto(evidence)

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceResponseDTO]:
        evidence = self.repository.get(evidence_id)
        if evidence:
            return self._to_dto(evidence)
        return None
