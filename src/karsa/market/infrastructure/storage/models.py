from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Table, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from karsa.shared.persistence.base import Base
from karsa.shared.persistence.mixins import UUIDMixin, TimestampMixin

# Association table for membership
universe_memberships = Table(
    'universe_memberships',
    Base.metadata,
    Column('universe_id', String(255), ForeignKey('market_universes.universe_id', ondelete='CASCADE'), primary_key=True),
    Column('asset_id', String(255), primary_key=True)
)

class MarketUniverseModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = 'market_universes'
    
    universe_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Relationship to members
    members = relationship('UniverseMemberModel', backref='universe', cascade='all, delete-orphan')

class UniverseMemberModel(Base):
    __tablename__ = 'universe_members_table' # Real mapped table instead of bare association for easier ORM manipulation if needed
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    universe_id = Column(String(255), ForeignKey('market_universes.universe_id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(String(255), nullable=False, index=True)

class MarketStructureSnapshotModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = 'market_structure_snapshots'
    
    snapshot_id = Column(String(255), unique=True, nullable=False, index=True)
    advancers = Column(Integer, nullable=False, default=0)
    decliners = Column(Integer, nullable=False, default=0)
    new_highs = Column(Integer, nullable=False, default=0)
    new_lows = Column(Integer, nullable=False, default=0)
    sector_strength = Column(JSON, nullable=False)
    foreign_flow_anomalies = Column(JSON, nullable=False)
