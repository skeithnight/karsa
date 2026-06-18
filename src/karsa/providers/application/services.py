from typing import Dict, Any, Optional
from datetime import datetime
from karsa.providers.domain.models import ProviderDefinition, ProviderHealth, DatalakeBlob

class ProviderRegistryService:
    def __init__(self, repository, uow):
        self.repository = repository
        self.uow = uow

    def register_provider(self, provider_id: str, name: str, ptype: str, config: Dict[str, Any]) -> ProviderDefinition:
        provider = ProviderDefinition(provider_id=provider_id, name=name, ptype=ptype, configuration=config)
        with self.uow:
            self.repository.add(provider)
            self.uow.commit()
        return provider

    def enable_provider(self, provider_id: str):
        with self.uow:
            provider = self.repository.get(provider_id)
            if provider:
                provider.enable()
                self.repository.save(provider)
            self.uow.commit()

    def disable_provider(self, provider_id: str):
        with self.uow:
            provider = self.repository.get(provider_id)
            if provider:
                provider.disable()
                self.repository.save(provider)
            self.uow.commit()

    def lookup_provider(self, provider_id: str) -> Optional[ProviderDefinition]:
        return self.repository.get(provider_id)


class ProviderHealthService:
    def __init__(self, repository, uow):
        self.repository = repository
        self.uow = uow

    def _get_or_create(self, provider_id: str) -> ProviderHealth:
        ph = self.repository.get_health(provider_id)
        if not ph:
            ph = ProviderHealth(provider_id=provider_id)
            self.repository.add_health(ph)
        return ph

    def record_success(self, provider_id: str, latency_ms: int):
        with self.uow:
            ph = self._get_or_create(provider_id)
            ph.record_success(latency_ms)
            self.repository.save_health(ph)
            self.uow.commit()

    def record_failure(self, provider_id: str):
        with self.uow:
            ph = self._get_or_create(provider_id)
            ph.record_failure()
            self.repository.save_health(ph)
            self.uow.commit()

    def get_status(self, provider_id: str) -> str:
        ph = self.repository.get_health(provider_id)
        return ph.status if ph else "UNKNOWN"


class DatalakeService:
    def __init__(self, repository, uow):
        self.repository = repository
        self.uow = uow

    def persist_payload(self, provider_id: str, asset_id: str, payload: Dict[str, Any], extracted_at: datetime, retention_until: Optional[datetime] = None) -> DatalakeBlob:
        blob = DatalakeBlob(provider_id=provider_id, asset_id=asset_id, payload=payload, extracted_at=extracted_at, retention_until=retention_until)
        with self.uow:
            self.repository.add_blob(blob)
            self.uow.commit()
        return blob

    def retrieve_payload(self, blob_id: str) -> Optional[DatalakeBlob]:
        return self.repository.get_blob(blob_id)
