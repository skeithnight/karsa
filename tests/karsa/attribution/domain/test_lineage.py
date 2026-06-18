from karsa.attribution.domain.model.lineage import AttributionLineage
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity

def test_lineage_advance_generation():
    identity = OutcomeSequenceIdentity("out_1", 1)
    lin = AttributionLineage(identity, "attr_1", 1)
    
    lin.advance_generation("attr_2")
    
    assert lin.current_generation == 2
    assert lin.active_attribution_id == "attr_2"
    assert lin.aggregate_version == 2
