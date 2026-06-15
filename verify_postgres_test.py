import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session
from decimal import Decimal
import json
import datetime
import os

from src.karsa.regime.domain.models import RegimeSession, RegimeSnapshot, RegimeTransition
from src.karsa.regime.domain.value_objects import RegimeClassification, SignalConfidenceScore
from src.karsa.regime.domain.repositories import ConcurrencyError, ImmutableUpdateError
from src.karsa.regime.infrastructure.postgres_regime_repositories import (
    PostgresRegimeSessionRepository, PostgresRegimeSnapshotRepository, PostgresRegimeTransitionRepository
)

@pytest.fixture(scope="module")
def pg_engine():
    engine = sa.create_engine('postgresql://postgres:postgres@localhost:5433/postgres')
    with engine.connect() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS regime_sessions CASCADE"))
        conn.execute(sa.text("DROP TABLE IF EXISTS regime_snapshots CASCADE"))
        conn.execute(sa.text("DROP TABLE IF EXISTS regime_transitions CASCADE"))
        
        conn.execute(sa.text("""
            CREATE TABLE regime_sessions (
                session_urn VARCHAR PRIMARY KEY,
                state VARCHAR NOT NULL,
                aggregate_version INTEGER NOT NULL
            )
        """))
        conn.execute(sa.text("""
            CREATE TABLE regime_snapshots (
                snapshot_urn VARCHAR,
                segment_urn VARCHAR NOT NULL,
                horizon_urn VARCHAR NOT NULL,
                snapshot_date VARCHAR NOT NULL,
                regime_classification VARCHAR NOT NULL,
                confidence_score NUMERIC NOT NULL,
                regime_manifest_hash VARCHAR NOT NULL,
                evidence_manifest_hash VARCHAR NOT NULL,
                methodology_metadata VARCHAR NOT NULL,
                aggregate_version INTEGER NOT NULL,
                calculated_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT true NOT NULL,
                PRIMARY KEY (snapshot_urn, calculated_at)
            )
        """))
        conn.execute(sa.text("CREATE UNIQUE INDEX ix_rs_nk ON regime_snapshots(segment_urn, horizon_urn, snapshot_date)"))
        conn.commit()
    return engine

@pytest.fixture
def db_session(pg_engine):
    with Session(pg_engine) as session:
        yield session
        session.rollback()

def test_occ_conflict(db_session):
    repo = PostgresRegimeSessionRepository(db_session)
    s = RegimeSession("urn:sess1", aggregate_version=1)
    repo.save(s)
    
    s.state = "ANALYZING"
    s.aggregate_version = 2
    repo.save(s)
    
    s_conflict = RegimeSession("urn:sess1", state="ANALYZING", aggregate_version=1)
    with pytest.raises(ConcurrencyError):
        repo.save(s_conflict)

def test_natural_key_uniqueness(db_session):
    repo = PostgresRegimeSnapshotRepository(db_session)
    c = RegimeClassification("BULL", "LOW", "HIGH")
    score = SignalConfidenceScore(Decimal('1.0'))

    snap1 = RegimeSnapshot(
        snapshot_urn="urn:snap:1", segment_urn="seg1", horizon_urn="hor1", snapshot_date="2026-06-15",
        regime_classification=c, confidence_score=score, regime_manifest_hash="r",
        evidence_manifest_hash="e", methodology_metadata={}
    )
    repo.save(snap1)

    snap2 = RegimeSnapshot(
        snapshot_urn="urn:snap:2", segment_urn="seg1", horizon_urn="hor1", snapshot_date="2026-06-15",
        regime_classification=c, confidence_score=score, regime_manifest_hash="r2",
        evidence_manifest_hash="e2", methodology_metadata={}
    )
    import sqlalchemy.exc
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        repo.save(snap2)
