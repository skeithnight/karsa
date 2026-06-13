import json
from dataclasses import asdict
from karsa.thesis.domain.model.value_objects import ThesisContextSnapshot

class ThesisSnapshotFactory:
    """Creates deterministic ThesisContextSnapshot from a Thesis aggregate."""
    
    @staticmethod
    def build(thesis) -> ThesisContextSnapshot:
        return ThesisContextSnapshot(
            thesis_id=thesis.identity.thesis_id,
            state=thesis.state.value,
            originator=asdict(thesis.originator) if thesis.originator else {},
            contributors=[asdict(c) for c in thesis.contributors],
            hypothesis=asdict(thesis.hypothesis),
            confidence=asdict(thesis.confidence),
            time_horizon=asdict(thesis.time_horizon),
            research_lineage=[asdict(r) for r in thesis.research_lineage],
            aggregate_version=thesis.aggregate_version
        )
