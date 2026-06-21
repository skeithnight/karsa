"""Tests for Capability Engine enums -- Sprint-11."""

from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
    EvolutionStatus,
    ScoreComponentName,
    ScoreTrend,
)


class TestEvolutionTriggerType:
    def test_all_values_are_strings(self):
        for member in EvolutionTriggerType:
            assert isinstance(member.value, str)
            assert member.value == member.name

    def test_review_finding(self):
        assert EvolutionTriggerType.REVIEW_FINDING == "REVIEW_FINDING"

    def test_attribution_insight(self):
        assert EvolutionTriggerType.ATTRIBUTION_INSIGHT == "ATTRIBUTION_INSIGHT"

    def test_execution_outcome(self):
        assert EvolutionTriggerType.EXECUTION_OUTCOME == "EXECUTION_OUTCOME"

    def test_governance_action(self):
        assert EvolutionTriggerType.GOVERNANCE_ACTION == "GOVERNANCE_ACTION"

    def test_four_members(self):
        assert len(EvolutionTriggerType) == 4


class TestEvolutionType:
    def test_all_values_are_strings(self):
        for member in EvolutionType:
            assert isinstance(member.value, str)
            assert member.value == member.name

    def test_five_members(self):
        assert len(EvolutionType) == 5


class TestEvolutionStatus:
    def test_canonical(self):
        assert EvolutionStatus.CANONICAL == "CANONICAL"

    def test_superseded(self):
        assert EvolutionStatus.SUPERSEDED == "SUPERSEDED"

    def test_experimental(self):
        assert EvolutionStatus.EXPERIMENTAL == "EXPERIMENTAL"

    def test_three_members(self):
        assert len(EvolutionStatus) == 3


class TestScoreComponentName:
    def test_four_components(self):
        assert len(ScoreComponentName) == 4

    def test_execution_quality(self):
        assert ScoreComponentName.EXECUTION_QUALITY == "EXECUTION_QUALITY"

    def test_attribution_alignment(self):
        assert (
            ScoreComponentName.ATTRIBUTION_ALIGNMENT == "ATTRIBUTION_ALIGNMENT"
        )

    def test_review_sentiment(self):
        assert ScoreComponentName.REVIEW_SENTIMENT == "REVIEW_SENTIMENT"

    def test_regime_fitness(self):
        assert ScoreComponentName.REGIME_FITNESS == "REGIME_FITNESS"


class TestScoreTrend:
    def test_four_members(self):
        assert len(ScoreTrend) == 4

    def test_improving(self):
        assert ScoreTrend.IMPROVING == "IMPROVING"

    def test_stable(self):
        assert ScoreTrend.STABLE == "STABLE"

    def test_declining(self):
        assert ScoreTrend.DECLINING == "DECLINING"

    def test_unknown(self):
        assert ScoreTrend.UNKNOWN == "UNKNOWN"
