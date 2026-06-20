from typing import Optional
from karsa.shared.domain.aggregate import VersionedAggregate
from karsa.attribution.domain.model.value_objects import OutcomeSequenceIdentity

class AttributionLineage(VersionedAggregate):
    def __init__(self, identity: OutcomeSequenceIdentity, active_attribution_id: str, current_generation: int, version: int = 1):
        super().__init__()
        self.identity = identity
        self.active_attribution_id = active_attribution_id
        self.current_generation = current_generation
        self._aggregate_version = version

    def advance_generation(self, new_attribution_id: str):
        self.current_generation += 1
        self.active_attribution_id = new_attribution_id
        self.increment_version()
