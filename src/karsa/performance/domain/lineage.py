from typing import List
from karsa.performance.domain.exceptions import TemporalLedgerError
from karsa.performance.domain.models import CalibrationLedgerEntry

def validate_calibration_ledger_lineage(entries: List[CalibrationLedgerEntry]):
    visited = set()
    for entry in entries:
        if entry.ledger_urn in visited:
            raise TemporalLedgerError(f"Cycle detected at ledger {entry.ledger_urn}")
        visited.add(entry.ledger_urn)
