from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from karsa.shared.persistence.base import Base
from karsa.shared.persistence.mixins import UUIDMixin, TimestampMixin

class ProviderDefinitionModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = 'provider_definitions'
    
    provider_id = Column(String(255), unique=True, nullable=False, index=True)
    provider_name = Column(String(255), nullable=False)
    provider_type = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    configuration = Column(JSON, nullable=False)

class ProviderHealthModel(UUIDMixin, Base):
    __tablename__ = 'provider_health'
    
    provider_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="UNKNOWN")
    latency_ms = Column(Integer, nullable=False, default=0)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class DatalakeBlobModel(UUIDMixin, Base):
    __tablename__ = 'provider_datalake_blobs'
    
    blob_id = Column(String(255), unique=True, nullable=False, index=True)
    provider_id = Column(String(255), nullable=False, index=True)
    asset_id = Column(String(255), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    extracted_at = Column(DateTime(timezone=True), nullable=False)
    retention_until = Column(DateTime(timezone=True), nullable=True)
