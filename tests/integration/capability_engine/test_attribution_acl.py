"""Tests for AttributionACL -- Sprint-11. Wave-8.

Scenario 2: AttributionDecompositionCompletedEvent -> AttributionACL
-> RecordCapabilityEvolutionCommand
Verifies: Mapping correctness. No Attribution Engine types leak.
"""

import pytest

from karsa.capability_engine.acl.attribution_acl import (
    AttributionACL,
    AttributionInsightPayload,
)
from karsa.capability_engine.contracts.record_capability_evolution import (
    RecordCapabilityEvolutionCommand,
)


@pytest.fixture
def acl():
    return AttributionACL()


class TestAttributionACLTranslation:
    """Attribution Engine events translated without type leakage."""

    def test_translate_attribution_insight(self, acl):
        payload = AttributionInsightPayload(
            attribution_id="urn:karsa:attribution:001",
            capability_family_id="acl-family-001",
            evaluation_id="acl-eval-001",
            capability_version_id="acl-ver-001",
            capability_urn="urn:karsa:capability:ns:acl-family-001:v1",
            score_before=0.5,
            score_after=0.65,
            lifecycle_state_before="ACTIVE",
            lifecycle_state_after="ACTIVE",
            source_id="urn:karsa:attribution:001",
            contribution_ids=["contrib-001", "contrib-002"],
            attribution_refs=[
                {
                    "contribution_id": "contrib-001",
                    "dimension": "THESIS",
                    "contribution_bps": 150.0,
                    "quality_score": 0.8,
                }
            ],
            capability_snapshot={"version": "v1"},
            attribution_snapshot={"total_bps": 150.0},
            evaluation_sequence=1,
            quality_score=0.9,
        )

        cmd = acl.translate_attribution_insight(payload)

        assert isinstance(cmd, RecordCapabilityEvolutionCommand)
        assert cmd.trigger_type == "ATTRIBUTION_INSIGHT"
        assert cmd.capability_family_id == "acl-family-001"
        assert cmd.before_score == 0.5
        assert cmd.after_score == 0.65
        assert cmd.score_change_bps == pytest.approx(1500.0)
        assert cmd.attribution_id == "urn:karsa:attribution:001"
        assert cmd.attribution_contribution_ids == [
            "contrib-001", "contrib-002"
        ]

    def test_translate_from_dict(self, acl):
        event_payload = {
            "attribution_id": "urn:karsa:attribution:002",
            "capability_family_id": "acl-family-002",
            "evaluation_id": "acl-eval-002",
            "capability_version_id": "acl-ver-002",
            "capability_urn": "urn:test",
            "score_before": 0.6,
            "score_after": 0.8,
            "lifecycle_state_before": "ACTIVE",
            "lifecycle_state_after": "ACTIVE",
            "source_id": "urn:karsa:attribution:002",
            "contribution_ids": ["contrib-003"],
            "attribution_refs": [],
            "capability_snapshot": {"version": "v1"},
            "attribution_snapshot": {},
            "evaluation_sequence": 2,
            "quality_score": 0.95,
        }

        cmd = acl.translate_from_dict(event_payload)

        assert isinstance(cmd, RecordCapabilityEvolutionCommand)
        assert cmd.trigger_type == "ATTRIBUTION_INSIGHT"
        assert cmd.score_change_bps == pytest.approx(2000.0)

    def test_no_attribution_types_in_command(self, acl):
        """The command must not contain Attribution Engine types."""
        payload = AttributionInsightPayload(
            attribution_id="urn:karsa:attribution:003",
            capability_family_id="acl-family-003",
            evaluation_id="acl-eval-003",
            capability_version_id="acl-ver-003",
            capability_urn="urn:test",
            score_before=0.5,
            score_after=0.7,
            lifecycle_state_before="ACTIVE",
            lifecycle_state_after="ACTIVE",
        )

        cmd = acl.translate_attribution_insight(payload)

        assert type(cmd).__module__ == "karsa.capability_engine.contracts.record_capability_evolution"

    def test_contribution_ids_preserved(self, acl):
        payload = AttributionInsightPayload(
            attribution_id="urn:karsa:attribution:004",
            capability_family_id="acl-family-004",
            evaluation_id="acl-eval-004",
            capability_version_id="acl-ver-004",
            capability_urn="urn:test",
            score_before=0.5,
            score_after=0.7,
            lifecycle_state_before="ACTIVE",
            lifecycle_state_after="ACTIVE",
            contribution_ids=["c-001", "c-002", "c-003"],
        )

        cmd = acl.translate_attribution_insight(payload)

        assert len(cmd.attribution_contribution_ids) == 3
        assert "c-001" in cmd.attribution_contribution_ids
