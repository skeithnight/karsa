from typing import List, Optional
from karsa.review.domain.models import ReviewRecord, PostMortemRecord

def reconstruct_review_lineage(records: List[ReviewRecord], start_record_urn: str) -> List[ReviewRecord]:
    """
    Reconstructs the lineage of ReviewRecords starting from start_record_urn.
    Walks the chain using superseded_by_version and/or invalidated_by_version pointers.
    """
    # Build maps for fast lookups
    by_urn = {r.record_urn: r for r in records}
    
    if start_record_urn not in by_urn:
        return []

    start_record = by_urn[start_record_urn]
    lineage = [start_record]
    visited = {start_record.record_urn}
    
    current = start_record
    while True:
        next_record = None
        target_version = current.superseded_by_version or current.invalidated_by_version
        
        if target_version is not None:
            # Look for a record in the same series with the target version
            for r in records:
                if (r.decision_id == current.decision_id and 
                        r.worker_urn == current.worker_urn and 
                        r.review_version == target_version):
                    next_record = r
                    break
        
        if next_record is None or next_record.record_urn in visited:
            break
            
        lineage.append(next_record)
        visited.add(next_record.record_urn)
        current = next_record
        
    return lineage


def reconstruct_postmortem_lineage(records: List[PostMortemRecord], start_postmortem_urn: str) -> List[PostMortemRecord]:
    """
    Reconstructs the lineage of PostMortemRecords starting from start_postmortem_urn.
    Walks the chain using superseded_by_version and/or invalidated_by_version pointers.
    """
    by_urn = {pm.postmortem_urn: pm for pm in records}
    
    if start_postmortem_urn not in by_urn:
        return []

    start_record = by_urn[start_postmortem_urn]
    lineage = [start_record]
    visited = {start_record.postmortem_urn}
    
    current = start_record
    while True:
        next_record = None
        target_version = current.superseded_by_version or current.invalidated_by_version
        
        if target_version is not None:
            for pm in records:
                if (pm.decision_id == current.decision_id and 
                        pm.postmortem_version == target_version):
                    next_record = pm
                    break
                    
        if next_record is None or next_record.postmortem_urn in visited:
            break
            
        lineage.append(next_record)
        visited.add(next_record.postmortem_urn)
        current = next_record
        
    return lineage
