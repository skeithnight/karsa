"""Tests for ReviewACL -- Sprint-11. Wave-8.

Scenario 1: ReviewFindingEvent -> ReviewACL -> RecordCapabilityEvolutionCommand
Verifies: No Review Engine types leak into Capability Engine.
"""

import pytest

from karsa.capability_engine.acl.review_acl import (
    ReviewACL,
    ReviewFindingPayload,
)
from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)


@pytest.fixture
def acl():
    return ReviewACL()


class TestReviewACLTranslation:
    """Review Engine events translated without type leakage."""

    def test_translate_review_finding(self, acl):
        payload = ReviewFindingPayload(
            review_id="urn:karsa:review:001",
            capability_family_id="acl-family-001",
            evaluation_id="acl-eval-001",
            capability_version_id="acl-ver-001",
            capability_urn="urn:karsa:capability:ns:acl-family-001:v1",
            score_before=0.5,
            score_after=0.7,
            lifecycle_state_before="ACTIVE",
            lifecycle_state_after="ACTIVE",
            source_id="urn:karsa:review:001",
            finding_ids=["finding-001"],
            findings=[{"type": "OPPORTUNITY", "severity": "MEDIUM"}],
            capability_snapshot={"version": "v1"},
            review_snapshot={"score": 0.7},
            evaluation_sequence=1,
            quality_score=0.8,
        )

        cmd = acl.translate_review_finding(payload)

        assert isinstance(cmd, RecordCapabilityEvolutionCommand)
        assert cmd.trigger_type == "REVIEW_FINDING"
        assert cmd.capability_family_id == "acl-family-001"
        assert cmd.before_score == 0.5
        assert cmd.after_score == 0.7
        assert cmd.score_change_bps == pytest.approx(2000.0)
        assert cmd.review_id == "urn:karsa:review:001"
        assert cmd.finding_ids == ["finding-001"]

    def test_translate_from_dict(self, acl):
        event_payload = {
            "review_id": "urn:karsa:review:002",
            "capability_family_id": "acl-family-002",
            "evaluation_id": "acl-eval-002",
            "capability_version_id": "acl-ver-002",
            "capability_urn": "urn:test",
            "score_before": 0.6,
            "score_after": 0.8,
            "lifecycle_state_before": "ACTIVE",
            "lifecycle_state_after": "ACTIVE",
            "source_id": "urn:karsa:review:002",
            "finding_ids": ["f-001"],
            "capability_snapshot": {"version": "v1"},
            "review_snapshot": {"score": 0.8},
            "evaluation_sequence": 1,
            "quality_score": 0.9,
        }

        cmd = acl.translate_from_dict(event_payload)

        assert isinstance(cmd, RecordCapabilityEvolutionCommand)
        assert cmd.trigger_type == "REVIEW_FINDING"
        assert cmd.before_score == 0.6
        assert cmd.after_score == 0.8

    def test_no_review_engine_types_in_command(self, acl):
        """The command contract must not contain any Review Engine types."""
        payload = ReviewFindingPayload(
            review_id="urn:karsa:review:003",
            capability_family_id="acl-family-003",
            evaluation_id="acl-eval-003",
            capability_version_id="acl-ver-003",
            capability_urn="urn:test",
            score_before=0.5,
            score_after=0.7,
            lifecycle_state_before="ACTIVE",
            lifecycle_state_after="ACTIVE",
        )

        cmd = acl.translate_review_finding(payload)

        # Verify the command is a contract type, not a domain type
        assert type(cmd).__module__ == "karsa.capability_engine.contracts.record_capability_evolution"

        # Verify no domain imports in the command
        cmd_dict = {
            k: v for k, v in cmd.__dict__.items() if v is not None
        }
        for key, value in cmd_dict.items():
            module = type(value).__module__
            assert "domain" not in module or isinstance(
                value, (str, int, float, bool, list, dict, tuple)
            )

    def test_bps_calculation_correct(self, acl):
        payload = ReviewFindingPayload(
            review_id="urn:test",
            capability_family_id="acl-family-004",
            evaluation_id="acl-eval-004",
            capability_version_id="acl-ver-004",
            capability_urn="urn:test",
            score_before=0.3,
            score_after=0.9,
            lifecycle_state_before="ACTIVE",
            lifecycle_state_after="ACTIVE",
        )

        cmd = acl.translate_review_finding(payload)

        assert cmd.score_change_bps == pytest.approx(6000.0)
