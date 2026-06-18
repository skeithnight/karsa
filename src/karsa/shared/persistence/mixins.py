from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func
from .types import GUID
import uuid

class UUIDMixin:
    """Provides a standard UUID primary key."""
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    """Provides standard created_at and updated_at audit fields."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class VersionMixin:
    """Provides standard optimistic concurrency version field."""
    version = Column(Integer, nullable=False, default=1)
