"""SQLAlchemy models for LLM Pool config tables."""
from sqlalchemy import Column, String, Integer, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from karsa.shared.persistence.base import Base
from karsa.shared.persistence.mixins import UUIDMixin


class LLMProviderModel(UUIDMixin, Base):
    __tablename__ = "llm_providers"

    name = Column(String(50), unique=True, nullable=False, index=True)
    base_url = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    priority = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    credentials = relationship("LLMProviderCredentialModel", back_populates="provider", cascade="all, delete-orphan")
    model_groups = relationship("LLMModelGroupModel", back_populates="provider", cascade="all, delete-orphan")


class LLMProviderCredentialModel(UUIDMixin, Base):
    __tablename__ = "llm_provider_credentials"

    provider_id = Column(ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    api_key_nonce = Column(Text, nullable=False, default="")
    api_secret_encrypted = Column(Text, nullable=True)
    api_secret_nonce = Column(Text, nullable=True)
    key_rotation_version = Column(Integer, nullable=False, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    provider = relationship("LLMProviderModel", back_populates="credentials")


class LLMModelGroupModel(UUIDMixin, Base):
    __tablename__ = "llm_model_groups"

    group_name = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    provider_id = Column(ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = Column(Integer, nullable=False, default=100)
    temperature = Column(Float, nullable=False, default=0.2)
    max_tokens = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    provider = relationship("LLMProviderModel", back_populates="model_groups")


class LLMRouterSettingsModel(Base):
    __tablename__ = "llm_router_settings"

    group_name = Column(String(50), primary_key=True)
    routing_strategy = Column(String(30), nullable=False, default="latency-based-routing")
    num_retries = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=60)
    allowed_fails = Column(Integer, nullable=False, default=2)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SystemConfigurationModel(Base):
    __tablename__ = "system_configurations"

    domain = Column(String(50), primary_key=True)
    config_key = Column(String(100), primary_key=True)
    config_value = Column(Text, nullable=False)  # JSONB stored as text in SQLite compat
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
