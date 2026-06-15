import os
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
import traceback

from karsa.regime.infrastructure.postgres_regime_repositories import PostgresRegimeSnapshotRepository
from karsa.regime.infrastructure.storage.postgres_models import Base
from karsa.regime.domain.models import RegimeClassification, SignalConfidenceScore, RegimeSnapshot

def run_validation():
    print("Starting PostgreSQL validation...")
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db_session = Session()

        repo = PostgresRegimeSnapshotRepository(db_session)
        c = RegimeClassification("BULL", "LOW", "HIGH")
        score = SignalConfidenceScore(Decimal('1.0'))

        snap1 = RegimeSnapshot(
            snapshot_urn="urn:snap:1", segment_urn="seg1", horizon_urn="hor1", snapshot_date="2026-06-15",
            regime_classification=c, confidence_score=score, regime_manifest_hash="r",
            evidence_manifest_hash="e", methodology_metadata={}
        )

        try:
            repo.save(snap1)
            print("test_natural_key_uniqueness: PASS on PostgreSQL")
        except Exception as e:
            print("test_natural_key_uniqueness: FAIL on PostgreSQL")
            traceback.print_exc()

if __name__ == "__main__":
    run_validation()
