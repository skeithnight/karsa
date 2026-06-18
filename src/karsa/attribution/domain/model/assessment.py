from datetime import datetime
from karsa.shared.domain.aggregate import VersionedAggregate

class AttributionAssessment(VersionedAggregate):
    """Aggregate summarizing the evaluation of an attribution lineage."""
    def __init__(
        self,
        assessment_id: str,
        lineage_id: str,
        fact_count: int,
        provenance_urn: str,
        aggregate_version: int = 1
    ):
        super().__init__(aggregate_version=aggregate_version)
        self.assessment_id = assessment_id
        self.lineage_id = lineage_id
        self.fact_count = fact_count
        self.provenance_urn = provenance_urn
        self.validate()

    def validate(self):
        if not self.assessment_id:
            raise ValueError("assessment_id is required")
        if not self.lineage_id:
            raise ValueError("lineage_id is required")
        if self.fact_count < 0:
            raise ValueError("fact_count cannot be negative")
        if not self.provenance_urn:
            raise ValueError("provenance_urn is required")
