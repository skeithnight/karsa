from .exceptions import LineageCycleError
from .models import ThesisTransition, ThesisSnapshot
from typing import List

def validate_transition_lineage(transitions: List[ThesisTransition]):
    visited = set()
    for t in transitions:
        if t.transition_urn in visited:
            raise LineageCycleError("Cycle detected")
        visited.add(t.transition_urn)

def validate_snapshot_lineage(snapshots: List[ThesisSnapshot]):
    visited = set()
    for s in snapshots:
        if s.snapshot_urn in visited:
            raise LineageCycleError("Cycle detected")
        visited.add(s.snapshot_urn)
