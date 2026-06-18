from typing import Optional
from sqlalchemy.orm import Session
from karsa.providers.domain.models import ProviderDefinition, ProviderHealth, DatalakeBlob
from karsa.providers.infrastructure.storage.models import ProviderDefinitionModel, ProviderHealthModel, DatalakeBlobModel

class ProviderRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, provider: ProviderDefinition):
        pm = ProviderDefinitionModel(
            provider_id=provider.provider_id,
            provider_name=provider.name,
            provider_type=provider.type,
            enabled=provider.enabled,
            configuration=provider.configuration
        )
        self.session.add(pm)

    def get(self, provider_id: str) -> Optional[ProviderDefinition]:
        pm = self.session.query(ProviderDefinitionModel).filter_by(provider_id=provider_id).first()
        if not pm:
            return None
        p = ProviderDefinition(pm.provider_id, pm.provider_name, pm.provider_type, pm.configuration)
        p.enabled = pm.enabled
        return p

    def save(self, provider: ProviderDefinition):
        pm = self.session.query(ProviderDefinitionModel).filter_by(provider_id=provider.provider_id).first()
        if pm:
            pm.enabled = provider.enabled
            pm.configuration = provider.configuration

    def add_health(self, health: ProviderHealth):
        hm = ProviderHealthModel(
            provider_id=health.provider_id,
            status=health.status,
            latency_ms=health.latency_ms,
            consecutive_failures=health.consecutive_failures
        )
        self.session.add(hm)

    def get_health(self, provider_id: str) -> Optional[ProviderHealth]:
        hm = self.session.query(ProviderHealthModel).filter_by(provider_id=provider_id).first()
        if not hm:
            return None
        h = ProviderHealth(provider_id=provider_id)
        h.status = hm.status
        h.latency_ms = hm.latency_ms
        h.consecutive_failures = hm.consecutive_failures
        return h

    def save_health(self, health: ProviderHealth):
        hm = self.session.query(ProviderHealthModel).filter_by(provider_id=health.provider_id).first()
        if hm:
            hm.status = health.status
            hm.latency_ms = health.latency_ms
            hm.consecutive_failures = health.consecutive_failures

    def add_blob(self, blob: DatalakeBlob):
        bm = DatalakeBlobModel(
            blob_id=blob.blob_id,
            provider_id=blob.provider_id,
            asset_id=blob.asset_id,
            payload=blob.payload,
            extracted_at=blob.extracted_at,
            retention_until=blob.retention_until
        )
        self.session.add(bm)

    def get_blob(self, blob_id: str) -> Optional[DatalakeBlob]:
        bm = self.session.query(DatalakeBlobModel).filter_by(blob_id=blob_id).first()
        if not bm:
            return None
        return DatalakeBlob(bm.provider_id, bm.asset_id, bm.payload, bm.extracted_at, bm.retention_until)
