from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True)
class RecomputationLineage:
    """Tracks historical restatements and superseding chains for attribution audits."""
    session_id: str
    superseded_session_id: str
    recomputation_timestamp: datetime


def reconstruct_lineage_chain(records: list) -> str:
    """
    Deterministically reconstruct the lineage transitions for a set of records
    without using chronological sorting or timestamps.
    """
    superseded_map = {}
    invalidated_map = {}
    versions = set()
    
    for r in records:
        v = r.attribution_version
        versions.add(v)
        if r.superseded_by_version is not None:
            superseded_map[v] = r.superseded_by_version
        if r.invalidated_by_version is not None:
            invalidated_map[v] = r.invalidated_by_version
            
    if not versions:
        return ""
        
    current = min(versions)
    path = [f"Version {current}"]
    
    while True:
        if current in superseded_map:
            nxt = superseded_map[current]
            path.append(f"\u2192 superseded by Version {nxt}")
            current = nxt
        elif current in invalidated_map:
            nxt = invalidated_map[current]
            path.append(f"\u2192 invalidated by Version {nxt}")
            current = nxt
        else:
            break
            
    return "\n".join(path)

