"""SQLAlchemy models for Data Bridge tables.

Sprint-51: Maps data_providers, provider_credentials,
provider_configurations, and provider_health_logs.
"""
import uuid

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from karsa.shared.persistence.base import Base
from karsa.shared.persistence.mixins import UUIDMixin


class DataBridgeProviderModel(UUIDMixin, Base):
    __tablename__ = "data_providers"

    name = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    priority = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    credentials = relationship("ProviderCredentialModel", back_populates="provider", cascade="all, delete-orphan")
    configurations = relationship("ProviderConfigurationModel", back_populates="provider", cascade="all, delete-orphan")
    health_logs = relationship("ProviderHealthLogModel", back_populates="provider", cascade="all, delete-orphan")


class ProviderCredentialModel(Base):
    """provider_credentials table — PK is provider_id (no separate id column)."""
    __tablename__ = "provider_credentials"

    provider_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_providers.id", ondelete="CASCADE"), primary_key=True)
    api_key_encrypted = Column(Text, nullable=False)
    api_key_nonce = Column(Text, nullable=False, default="")
    api_secret_encrypted = Column(Text, nullable=True)
    api_secret_nonce = Column(Text, nullable=True)
    key_rotation_version = Column(Integer, nullable=False, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    provider = relationship("DataBridgeProviderModel", back_populates="credentials")


class ProviderConfigurationModel(UUIDMixin, Base):
    __tablename__ = "provider_configurations"

    provider_id = Column(ForeignKey("data_providers.id", ondelete="CASCADE"), nullable=False)
    config_key = Column(String(100), nullable=False)
    config_value = Column(JSONB, nullable=False)

    # Relationship
    provider = relationship("DataBridgeProviderModel", back_populates="configurations")

    __table_args__ = (
        {"comment": "Unique constraint on (provider_id, config_key) enforced by DB"},
    )


class ProviderHealthLogModel(UUIDMixin, Base):
    __tablename__ = "provider_health_logs"

    provider_id = Column(ForeignKey("data_providers.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    provider = relationship("DataBridgeProviderModel", back_populates="health_logs")
