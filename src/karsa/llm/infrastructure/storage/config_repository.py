"""Repository for LLM Pool config persistence."""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from karsa.llm.domain.config_models import (
    LLMProvider,
    LLMProviderStatus,
    LLMCredential,
    LLMModelGroupEntry,
    LLMRouterSettings,
)
from karsa.llm.infrastructure.storage.config_models import (
    LLMProviderModel,
    LLMProviderCredentialModel,
    LLMModelGroupModel,
    LLMRouterSettingsModel,
    SystemConfigurationModel,
)


class LLMConfigRepository:
    """CRUD for LLM Pool configuration tables."""

    def __init__(self, session: Session):
        self.session = session

    # --- Provider CRUD ---

    def add_provider(self, provider: LLMProvider) -> None:
        pm = LLMProviderModel(
            id=provider.provider_id,
            name=provider.name,
            base_url=provider.base_url,
            status=provider.status.value,
            priority=provider.priority,
        )
        self.session.add(pm)

    def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        pm = self.session.query(LLMProviderModel).filter_by(id=provider_id).first()
        if not pm:
            return None
        return self._to_provider(pm)

    def get_provider_by_name(self, name: str) -> Optional[LLMProvider]:
        pm = self.session.query(LLMProviderModel).filter_by(name=name).first()
        if not pm:
            return None
        return self._to_provider(pm)

    def list_providers(self) -> List[LLMProvider]:
        pms = self.session.query(LLMProviderModel).order_by("priority").all()
        return [self._to_provider(pm) for pm in pms]

    def save_provider(self, provider: LLMProvider) -> None:
        pm = self.session.query(LLMProviderModel).filter_by(id=provider.provider_id).first()
        if pm:
            pm.name = provider.name
            pm.base_url = provider.base_url
            pm.status = provider.status.value
            pm.priority = provider.priority

    # --- Credential CRUD ---

    def save_credential(self, provider_id: str, credential: LLMCredential) -> None:
        existing = self.session.query(LLMProviderCredentialModel).filter_by(provider_id=provider_id).first()
        if existing:
            existing.api_key_encrypted = credential.ciphertext
            existing.api_key_nonce = credential.nonce
            existing.key_rotation_version = credential.key_rotation_version
            existing.expires_at = credential.expires_at
        else:
            cm = LLMProviderCredentialModel(
                provider_id=provider_id,
                api_key_encrypted=credential.ciphertext,
                api_key_nonce=credential.nonce,
                key_rotation_version=credential.key_rotation_version,
                expires_at=credential.expires_at,
            )
            self.session.add(cm)

    def get_credential(self, provider_id: str) -> Optional[LLMCredential]:
        cm = self.session.query(LLMProviderCredentialModel).filter_by(provider_id=provider_id).first()
        if not cm:
            return None
        return LLMCredential(
            ciphertext=cm.api_key_encrypted,
            nonce=cm.api_key_nonce or "",
            key_rotation_version=cm.key_rotation_version,
            expires_at=cm.expires_at,
        )

    # --- Model Group CRUD ---

    def add_model_group(self, group_name: str, entry: LLMModelGroupEntry) -> None:
        gm = LLMModelGroupModel(
            group_name=group_name,
            model_name=entry.model_name,
            provider_id=entry.provider_id,
            priority=entry.priority,
            temperature=entry.temperature,
            max_tokens=entry.max_tokens,
            is_active=entry.is_active,
        )
        self.session.add(gm)

    def get_model_group(self, group_name: str) -> List[LLMModelGroupEntry]:
        gms = (
            self.session.query(LLMModelGroupModel)
            .filter_by(group_name=group_name, is_active=True)
            .order_by("priority")
            .all()
        )
        return [
            LLMModelGroupEntry(
                model_name=gm.model_name,
                provider_id=str(gm.provider_id),
                priority=gm.priority,
                temperature=gm.temperature,
                max_tokens=gm.max_tokens,
                is_active=gm.is_active,
            )
            for gm in gms
        ]

    def remove_model_group_entry(self, group_name: str, model_name: str, provider_id: str) -> None:
        gm = (
            self.session.query(LLMModelGroupModel)
            .filter_by(group_name=group_name, model_name=model_name, provider_id=provider_id)
            .first()
        )
        if gm:
            self.session.delete(gm)

    # --- Router Settings CRUD ---

    def save_router_settings(self, settings: LLMRouterSettings) -> None:
        existing = self.session.query(LLMRouterSettingsModel).filter_by(group_name=settings.group_name).first()
        if existing:
            existing.routing_strategy = settings.routing_strategy
            existing.num_retries = settings.num_retries
            existing.timeout_seconds = settings.timeout_seconds
            existing.allowed_fails = settings.allowed_fails
        else:
            rm = LLMRouterSettingsModel(
                group_name=settings.group_name,
                routing_strategy=settings.routing_strategy,
                num_retries=settings.num_retries,
                timeout_seconds=settings.timeout_seconds,
                allowed_fails=settings.allowed_fails,
            )
            self.session.add(rm)

    def get_router_settings(self, group_name: str) -> Optional[LLMRouterSettings]:
        rm = self.session.query(LLMRouterSettingsModel).filter_by(group_name=group_name).first()
        if not rm:
            return None
        return LLMRouterSettings(
            group_name=rm.group_name,
            routing_strategy=rm.routing_strategy,
            num_retries=rm.num_retries,
            timeout_seconds=rm.timeout_seconds,
            allowed_fails=rm.allowed_fails,
            updated_at=rm.updated_at,
        )

    # --- System Config CRUD ---

    def save_system_config(self, domain: str, key: str, value: Any, description: str = "") -> None:
        import json
        existing = self.session.query(SystemConfigurationModel).filter_by(domain=domain, config_key=key).first()
        if existing:
            existing.config_value = json.dumps(value)
            existing.description = description
        else:
            cm = SystemConfigurationModel(
                domain=domain,
                config_key=key,
                config_value=json.dumps(value),
                description=description,
            )
            self.session.add(cm)

    def get_system_config(self, domain: str, key: str) -> Optional[Any]:
        import json
        cm = self.session.query(SystemConfigurationModel).filter_by(domain=domain, config_key=key).first()
        if not cm:
            return None
        return json.loads(cm.config_value)

    def get_all_system_configs(self, domain: str) -> Dict[str, Any]:
        import json
        cms = self.session.query(SystemConfigurationModel).filter_by(domain=domain).all()
        return {cm.config_key: json.loads(cm.config_value) for cm in cms}

    # --- Helper ---

    def _to_provider(self, pm: LLMProviderModel) -> LLMProvider:
        provider = LLMProvider.__new__(LLMProvider)
        provider.provider_id = str(pm.id)
        provider.aggregate_id = str(pm.id)
        provider.name = pm.name
        provider.base_url = pm.base_url
        provider.status = LLMProviderStatus(pm.status)
        provider.priority = pm.priority
        provider.created_at = pm.created_at
        provider._domain_events = []
        provider._version = 0
        return provider
