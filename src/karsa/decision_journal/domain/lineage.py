from typing import List
from karsa.decision_journal.domain.exceptions import TemporalLineageError, CryptographicIntegrityError
from karsa.decision_journal.domain.models import DecisionJournalEntry
from karsa.decision_journal.domain.value_objects import JournalHash

def validate_journal_lineage(entries: List[DecisionJournalEntry]):
    # Sort entries by chronological creation
    sorted_entries = sorted(entries, key=lambda x: x.created_at)
    
    visited = set()
    for i, entry in enumerate(sorted_entries):
        if entry.journal_urn in visited:
            raise TemporalLineageError(f"Cycle detected at journal {entry.journal_urn}")
        visited.add(entry.journal_urn)
        
        # Cryptographic validation
        prev_hash = None
        if entry.previous_journal_urn:
            # Find previous entry to get its hash
            prev_entry = next((e for e in sorted_entries if e.journal_urn == entry.previous_journal_urn), None)
            if not prev_entry:
                raise TemporalLineageError(f"Missing lineage parent {entry.previous_journal_urn}")
            prev_hash = prev_entry.journal_hash.hash_value
            
        expected_hash = JournalHash.generate(entry.journal_urn, entry.thesis_urn, prev_hash)
        if entry.journal_hash.hash_value != expected_hash.hash_value:
            raise CryptographicIntegrityError(f"Hash mismatch at {entry.journal_urn}")
