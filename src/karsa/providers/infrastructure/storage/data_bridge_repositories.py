"""Repository layer for Data Bridge persistence.

Sprint-51: CRUD for data_providers, provider_credentials,
provider_configurations. Append-only for provider_health_logs.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from karsa.providers.domain.data_bridge import (
    DataBridgeProvider,
    ProviderType,
    ProviderStatus,
    EncryptedCredential,
    ProviderConfig,
    HealthLogEntry,
    HealthStatus,
)
from karsa.providers.infrastructure.storage.data_bridge_models import (
    DataBridgeProviderModel,
    ProviderCredentialModel,
    ProviderConfigurationModel,
    ProviderHealthLogModel,
)


class DataBridgeProviderRepository:
    """CRUD operations for Data Bridge provider management."""

    def __init__(self, session: Session):
        self.session = session

    # --- Provider CRUD ---

    def add(self, provider: DataBridgeProvider) -> None:
        pm = DataBridgeProviderModel(
            id=provider.provider_id,
            name=provider.name,
            type=provider.type.value,
            status=provider.status.value,
            priority=provider.priority,
        )
        self.session.add(pm)

    def get(self, provider_id: str) -> Optional[DataBridgeProvider]:
        pm = self.session.query(DataBridgeProviderModel).filter_by(id=provider_id).first()
        if not pm:
            return None
        return self._to_domain(pm)

    def get_by_name(self, name: str) -> Optional[DataBridgeProvider]:
        pm = self.session.query(DataBridgeProviderModel).filter_by(name=name).first()
        if not pm:
            return None
        return self._to_domain(pm)

    def list_active(self) -> List[DataBridgeProvider]:
        pms = self.session.query(DataBridgeProviderModel).filter_by(status="active").order_by("priority").all()
        return [self._to_domain(pm) for pm in pms]

    def list_by_type(self, ptype: str) -> List[DataBridgeProvider]:
        pms = self.session.query(DataBridgeProviderModel).filter_by(type=ptype, status="active").all()
        return [self._to_domain(pm) for pm in pms]

    def save(self, provider: DataBridgeProvider) -> None:
        pm = self.session.query(DataBridgeProviderModel).filter_by(id=provider.provider_id).first()
        if pm:
            pm.name = provider.name
            pm.type = provider.type.value
            pm.status = provider.status.value
            pm.priority = provider.priority

    # --- Credential CRUD ---

    def save_credential(
        self,
        provider_id: str,
        encrypted_key: EncryptedCredential,
        encrypted_secret: Optional[EncryptedCredential] = None,
    ) -> None:
        existing = self.session.query(ProviderCredentialModel).filter_by(provider_id=provider_id).first()
        if existing:
            existing.api_key_encrypted = encrypted_key.ciphertext
            existing.api_key_nonce = encrypted_key.nonce
            existing.api_secret_encrypted = encrypted_secret.ciphertext if encrypted_secret else None
            existing.api_secret_nonce = encrypted_secret.nonce if encrypted_secret else None
            existing.key_rotation_version = encrypted_key.key_rotation_version
            existing.expires_at = encrypted_key.expires_at
        else:
            cm = ProviderCredentialModel(
                provider_id=provider_id,
                api_key_encrypted=encrypted_key.ciphertext,
                api_key_nonce=encrypted_key.nonce,
                api_secret_encrypted=encrypted_secret.ciphertext if encrypted_secret else None,
                api_secret_nonce=encrypted_secret.nonce if encrypted_secret else None,
                key_rotation_version=encrypted_key.key_rotation_version,
                expires_at=encrypted_key.expires_at,
            )
            self.session.add(cm)

    def get_credential(self, provider_id: str) -> Optional[EncryptedCredential]:
        cm = self.session.query(ProviderCredentialModel).filter_by(provider_id=provider_id).first()
        if not cm:
            return None
        return EncryptedCredential(
            ciphertext=cm.api_key_encrypted,
            nonce=cm.api_key_nonce or "",
            key_rotation_version=cm.key_rotation_version,
            expires_at=cm.expires_at,
        )

    # --- Configuration CRUD ---

    def save_config(self, provider_id: str, config_key: str, config_value: Dict[str, Any]) -> None:
        existing = (
            self.session.query(ProviderConfigurationModel)
            .filter_by(provider_id=provider_id, config_key=config_key)
            .first()
        )
        if existing:
            existing.config_value = config_value
        else:
            cm = ProviderConfigurationModel(
                provider_id=provider_id,
                config_key=config_key,
                config_value=config_value,
            )
            self.session.add(cm)

    def get_config(self, provider_id: str, config_key: str) -> Optional[Dict[str, Any]]:
        cm = (
            self.session.query(ProviderConfigurationModel)
            .filter_by(provider_id=provider_id, config_key=config_key)
            .first()
        )
        return cm.config_value if cm else None

    def get_all_configs(self, provider_id: str) -> Dict[str, Any]:
        configs = (
            self.session.query(ProviderConfigurationModel)
            .filter_by(provider_id=provider_id)
            .all()
        )
        return {c.config_key: c.config_value for c in configs}

    # --- Helper ---

    def _to_domain(self, pm: DataBridgeProviderModel) -> DataBridgeProvider:
        """Reconstruct aggregate from persistence model (without re-emitting events)."""
        provider = DataBridgeProvider.__new__(DataBridgeProvider)
        provider.provider_id = str(pm.id)
        provider.aggregate_id = str(pm.id)
        provider.name = pm.name
        provider.type = ProviderType(pm.type)
        provider.status = ProviderStatus(pm.status)
        provider.priority = pm.priority
        provider.created_at = pm.created_at
        provider._domain_events = []
        provider._version = 0
        return provider


class ProviderHealthLogRepository:
    """Append-only writes to provider_health_logs."""

    def __init__(self, session: Session):
        self.session = session

    def append(self, entry: HealthLogEntry) -> None:
        lm = ProviderHealthLogModel(
            id=entry.log_id,
            provider_id=entry.provider_id,
            status=entry.status.value,
            error_message=entry.error_message,
            latency_ms=entry.latency_ms,
            recorded_at=entry.recorded_at,
        )
        self.session.add(lm)
        self.session.commit()

    def get_recent(
        self,
        provider_id: str,
        limit: int = 50,
    ) -> List[HealthLogEntry]:
        logs = (
            self.session.query(ProviderHealthLogModel)
            .filter_by(provider_id=provider_id)
            .order_by(ProviderHealthLogModel.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return [
            HealthLogEntry(
                log_id=str(l.id),
                provider_id=l.provider_id,
                status=HealthStatus(l.status),
                error_message=l.error_message,
                latency_ms=l.latency_ms,
                recorded_at=l.recorded_at,
            )
            for l in logs
        ]
