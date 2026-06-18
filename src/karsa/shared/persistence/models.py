from sqlalchemy import Column, String, Integer, JSON, BigInteger, DateTime, UniqueConstraint, Text
from sqlalchemy.sql import func
from .base import Base
from .mixins import UUIDMixin

class EventJournal(UUIDMixin, Base):
    """Immutable event journal for event sourcing."""
    __tablename__ = 'event_journal'
    __table_args__ = (UniqueConstraint('stream_id', 'stream_version', name='uq_event_journal_stream_version'),)

    # Global monotonic sequence id
    sequence_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Domain grouping
    stream_id = Column(String(255), nullable=False, index=True)
    stream_version = Column(Integer, nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    aggregate_type = Column(String(100), nullable=False)
    
    # Event data
    event_id = Column(String(36), nullable=False, unique=True, index=True)
    event_type = Column(String(255), nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    
    # Audit
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EventOutbox(UUIDMixin, Base):
    """Transactional outbox for reliable event publishing."""
    __tablename__ = 'event_outbox'
    
    # Event data
    event_id = Column(String(36), nullable=False, unique=True, index=True)
    stream_id = Column(String(255), nullable=False)
    aggregate_type = Column(String(100), nullable=False)
    event_name = Column(String(255), nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    
    # Status
    published = Column(Integer, default=0, index=True) # 0=pending, 1=published
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0, server_default='0')
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
