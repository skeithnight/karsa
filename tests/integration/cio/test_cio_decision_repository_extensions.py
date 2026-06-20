"""Tests for CIODecisionRepository extensions — Sprint-06 Wave-3."""
import pytest
from datetime import datetime
from typing import Optional, List, Dict

from karsa.cio.models import CIODecisionAggregate
from karsa.cio.value_objects import CommitteeVote
from karsa.cio.repositories import InMemoryCIODecisionRepository
from karsa.cio.exceptions import ImmutabilityViolationException, DuplicateJournalRefException


def _make_decision(decision_id="dec-1", proposal_id=None, journal_ref=None):
    if journal_ref is None:
        journal_ref = f"urn:karsa:journal:{decision_id}"
    return CIODecisionAggregate(
        decision_id=decision_id,
        calculation_id=None,
        governance_exception_id=None,
        decision_journal_ref=journal_ref,
        portfolio_snapshot_hash="hash123",
        action_type="APPROVE_ALLOCATION",
        target_node_type="WORKER",
        target_node_id="portfolio-main",
        decision_payload={"allocated_weights": {"w1": 0.5}},
        cryptographic_signature="sig_base64",
        created_at=datetime.utcnow(),
        votes=[CommitteeVote(voter_id="cio-1", vote_type="APPROVE", timestamp=datetime.utcnow())],
        proposal_id=proposal_id,
    )


class TestGetDecisionsByProposalId:
    def test_returns_decisions_for_proposal(self):
        repo = InMemoryCIODecisionRepository()
        repo.save_decision(_make_decision("dec-1", proposal_id="urn:karsa:proposal:p1"))
        repo.save_decision(_make_decision("dec-2", proposal_id="urn:karsa:proposal:p1"))
        repo.save_decision(_make_decision("dec-3", proposal_id="urn:karsa:proposal:p2"))

        results = repo.get_decisions_by_proposal_id("urn:karsa:proposal:p1")
        assert len(results) == 2
        assert all(d.proposal_id == "urn:karsa:proposal:p1" for d in results)

    def test_returns_empty_for_nonexistent_proposal(self):
        repo = InMemoryCIODecisionRepository()
        results = repo.get_decisions_by_proposal_id("nonexistent")
        assert results == []

    def test_returns_empty_when_no_proposals(self):
        repo = InMemoryCIODecisionRepository()
        repo.save_decision(_make_decision("dec-1", proposal_id=None))
        results = repo.get_decisions_by_proposal_id("any")
        assert results == []


class TestExistsByJournalRef:
    def test_exists_true(self):
        repo = InMemoryCIODecisionRepository()
        repo.save_decision(_make_decision(journal_ref="urn:karsa:journal:j1"))
        assert repo.exists_by_journal_ref("urn:karsa:journal:j1") is True

    def test_exists_false(self):
        repo = InMemoryCIODecisionRepository()
        assert repo.exists_by_journal_ref("nonexistent") is False

    def test_different_journal_ref(self):
        repo = InMemoryCIODecisionRepository()
        repo.save_decision(_make_decision(journal_ref="urn:karsa:journal:j1"))
        assert repo.exists_by_journal_ref("urn:karsa:journal:j2") is False


class TestJournalUniquenessEnforcement:
    def test_duplicate_journal_ref_raises(self):
        repo = InMemoryCIODecisionRepository()
        repo.save_decision(_make_decision("dec-1", journal_ref="urn:karsa:journal:j1"))
        with pytest.raises(DuplicateJournalRefException):
            repo.save_decision(_make_decision("dec-2", journal_ref="urn:karsa:journal:j1"))

    def test_different_journal_refs_allowed(self):
        repo = InMemoryCIODecisionRepository()
        repo.save_decision(_make_decision("dec-1", journal_ref="urn:karsa:journal:j1"))
        repo.save_decision(_make_decision("dec-2", journal_ref="urn:karsa:journal:j2"))
        assert len(repo.list_decisions()) == 2
