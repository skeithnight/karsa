class DecisionJournalError(Exception):
    """Base exception for Decision Journal."""
    pass

class InvalidConfidenceError(DecisionJournalError):
    pass

class TemporalLineageError(DecisionJournalError):
    pass

class CryptographicIntegrityError(DecisionJournalError):
    pass
