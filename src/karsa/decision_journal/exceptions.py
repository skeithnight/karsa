class DecisionJournalException(Exception):
    """Base exception for Decision Journal bounded context."""
    pass

class ImmutabilityViolationException(DecisionJournalException):
    """Raised when an attempt is made to modify an immutable aggregate or database record."""
    pass

class HindsightValidationException(DecisionJournalException):
    """Raised when an action violates hindsight prevention rules (e.g. posting a revision post-outcome)."""
    pass

class LineageIntegrityException(DecisionJournalException):
    """Raised when a lineage verification check fails (e.g. parent pointer cycle or orphan record)."""
    pass

class VerificationFailedException(DecisionJournalException):
    """Raised when a context hash verification check fails."""
    pass

class ActiveLeafNotFoundException(DecisionJournalException):
    """Raised when the active leaf node of a decision lineage cannot be resolved."""
    pass
