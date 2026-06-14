from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity

def test_attribution_lineage_creation():
    identity = OutcomeSequenceIdentity(outcome_id="out-123", sequence_id=1)
    lineage = AttributionLineage(
        identity=identity,
        active_attribution_id="attr-initial",
        current_generation=1,
        version=1
    )
    assert lineage.identity.outcome_id == "out-123"
    assert lineage.identity.sequence_id == 1
    assert lineage.active_attribution_id == "attr-initial"
    assert lineage.current_generation == 1
    assert lineage.aggregate_version == 1

def test_attribution_lineage_advance_generation():
    identity = OutcomeSequenceIdentity(outcome_id="out-123", sequence_id=1)
    lineage = AttributionLineage(
        identity=identity,
        active_attribution_id="attr-initial",
        current_generation=1,
        version=1
    )
    lineage.advance_generation("attr-new")
    assert lineage.active_attribution_id == "attr-new"
    assert lineage.current_generation == 2
    assert lineage.aggregate_version == 2

