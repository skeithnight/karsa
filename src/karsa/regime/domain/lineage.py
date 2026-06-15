from typing import List, Dict, Optional, Any

class LineageCycleError(Exception):
    pass

def reconstruct_transition_lineage(transitions: List[Any], start_urn: str) -> List[Any]:
    urn_map = {t.transition_urn: t for t in transitions}
    current_urn = start_urn
    lineage = []
    visited = set()

    while current_urn:
        if current_urn in visited:
            raise LineageCycleError(f"Cycle detected at URN {current_urn}")
        
        visited.add(current_urn)
        transition = urn_map.get(current_urn)
        
        if not transition:
            break
            
        lineage.append(transition)
        current_urn = transition.supersedes_transition_urn
        
    return lineage

# Note: RegimeSnapshot is immutable, but we might have a superseded_by_snapshot_urn 
# or similar in metadata. Since RegimeSnapshot model in models.py does not explicitly have supersedes pointers, 
# assuming we can just demonstrate cycle detection on arbitrary objects that have a pointer.
# I'll add supersedes_snapshot_urn to RegimeSnapshot dynamically or expect it as a property if needed.
# Since the prompt said "reconstruct_snapshot_lineage()", let's build it generically.

def reconstruct_snapshot_lineage(snapshots: List[Any], start_urn: str, pointer_attr: str = "supersedes_snapshot_urn") -> List[Any]:
    urn_map = {s.snapshot_urn: s for s in snapshots}
    current_urn = start_urn
    lineage = []
    visited = set()

    while current_urn:
        if current_urn in visited:
            raise LineageCycleError(f"Cycle detected at URN {current_urn}")
        
        visited.add(current_urn)
        snapshot = urn_map.get(current_urn)
        
        if not snapshot:
            break
            
        lineage.append(snapshot)
        current_urn = getattr(snapshot, pointer_attr, None)
        
    return lineage
