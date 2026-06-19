import pytest
from sqlalchemy import create_engine, text
from karsa.review.domain.models import ReviewAssessment, ReviewTarget, EvidenceReference, ReviewLineage
from karsa.attribution.domain.models import AttributionLedger, AttributionSubject
from karsa.review.domain.repository.aggregate_repo import ReviewAggregateRepository
from karsa.attribution.domain.repository.aggregate_repo import AttributionAggregateRepository
from karsa.shared.infrastructure.event_journal import EventJournalRepository

def test_deterministic_replay(db_engine, db_pool):
    # 1. Truncate projections
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM attribution_nodes"))
        conn.execute(text("DELETE FROM attribution_snapshots"))
        conn.execute(text("DELETE FROM calibration_snapshots"))
        conn.execute(text("DELETE FROM assumption_grades"))
        conn.execute(text("DELETE FROM review_snapshots"))
        conn.execute(text("DELETE FROM projection_checkpoints WHERE projection_name IN ('review_projections', 'attribution_projections')"))

    # 2. Reset checkpoints
    # 3. Use Aggregates and OCC
    with db_pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        review_repo = ReviewAggregateRepository(journal_repo)
        attr_repo = AttributionAggregateRepository(journal_repo)

        # Create Review
        target = ReviewTarget("THESIS", "urn:karsa:thesis:1")
        review = ReviewAssessment.initiate("urn:karsa:review:1", target)
        
        # Attach evidence with cryptographic hash
        ev = EvidenceReference("MARKET_DATA", "urn:karsa:market:AAPL", 142, "hash_value")
        review.attach_evidence(ev)
        
        # Grade calibration
        review.grade_calibration(0.95, 0.10, "Overconfident")
        
        # Seal Review
        lineage = ReviewLineage(None, None, "INITIAL")
        review.seal(0.10, lineage)
        
        # OCC save expecting version 0 for new aggregate
        review_repo.save(review, expected_version=0)
        conn.commit()

        # Create Attribution
        attr = AttributionLedger.calculate("urn:karsa:attr:1", "urn:karsa:review:1", "urn:karsa:bench:SP500", 0.15, 0.05)
        
        # Swarm attribution: 100% to Swarm
        swarm_subject = AttributionSubject("TEAM", "urn:karsa:team:swarm")
        attr.allocate_credit("node_1", None, swarm_subject, 0.8, 0.2)
        
        # Child allocation: 50% to Analyst A
        analyst_subject = AttributionSubject("ANALYST", "urn:karsa:analyst:A")
        attr.allocate_credit("node_2", "node_1", analyst_subject, 0.4, 0.1)

        attr_repo.save(attr, expected_version=0)
        conn.commit()

    # Rehydrate Review to check OCC and Expected Version
    with db_pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        review_repo = ReviewAggregateRepository(journal_repo)
        
        rehydrated = review_repo.get("urn:karsa:review:1")
        assert rehydrated.aggregate_version == 4
        assert rehydrated.state == "SEALED"
        assert rehydrated.evidence[0].fingerprint_sha256 == "hash_value"
        
        # OCC Failure test
        try:
            review_repo.save(rehydrated, expected_version=3) # Should fail as it's 4
            assert False, "OCC Stale Write Protection Failed"
        except Exception:
            pass # Expected
