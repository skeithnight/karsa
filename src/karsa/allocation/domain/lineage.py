from typing import List
from karsa.allocation.domain.models import AllocationDecisionRecord

def reconstruct_allocation_lineage(
    records: List[AllocationDecisionRecord],
    start_record_urn: str
) -> List[AllocationDecisionRecord]:
    """
    Reconstructs the lineage of AllocationDecisionRecords starting from start_record_urn.
    Walks backward to find the root node, and then walks forward to reconstruct the chronological sequence.
    Uses pointer traversal (supersedes_record_urn/invalidates_record_urn) with visited set loop protection.
    """
    by_urn = {r.record_urn: r for r in records}
    if start_record_urn not in by_urn:
        return []

    # 1. Walk backward to find the root of the lineage
    current = by_urn[start_record_urn]
    visited_backward = {current.record_urn}
    while True:
        prev_urn = current.supersedes_record_urn or current.invalidates_record_urn
        if not prev_urn or prev_urn not in by_urn or prev_urn in visited_backward:
            break
        current = by_urn[prev_urn]
        visited_backward.add(current.record_urn)

    root = current

    # 2. Walk forward from the root to build the complete chronological lineage
    lineage = [root]
    visited_forward = {root.record_urn}
    current = root

    # Map predecessor URN to the record that superseded/invalidated it
    predecessor_to_next = {}
    for r in records:
        if r.supersedes_record_urn:
            predecessor_to_next[r.supersedes_record_urn] = r
        if r.invalidates_record_urn:
            predecessor_to_next[r.invalidates_record_urn] = r

    while True:
        next_rec = predecessor_to_next.get(current.record_urn)
        if not next_rec or next_rec.record_urn in visited_forward:
            break
        lineage.append(next_rec)
        visited_forward.add(next_rec.record_urn)
        current = next_rec

    return lineage
