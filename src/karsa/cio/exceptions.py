class CIODecisionException(Exception):
    """Base exception for CIO Engine bounded context."""
    pass

class ImmutabilityViolationException(CIODecisionException):
    """Raised when an attempt is made to update or delete a write-once ledger record."""
    pass

class QuorumNotMetException(CIODecisionException):
    """Raised when the consensus quorum checks fail on committee votes."""
    pass

class InvalidDecisionSignatureException(CIODecisionException):
    """Raised when a cryptographic signature check fails."""
    pass

class DecisionNotFoundException(CIODecisionException):
    """Raised when a requested decision URN cannot be resolved."""
    pass

class DuplicateJournalRefException(CIODecisionException):
    """Raised when a duplicate Decision Journal reference is submitted."""
    pass
