class ImmutabilityViolationException(Exception):
    """Raised when an update or delete is attempted on an immutable ledger entry."""
    pass

class NegativeEigenvalueException(ValueError):
    """Raised when a covariance matrix has non-positive eigenvalues."""
    pass

class InvalidSnapshotURNException(ValueError):
    """Raised when a portfolio snapshot URN format is invalid."""
    pass

class InvalidValueException(ValueError):
    """Raised when a risk metric value is logically invalid."""
    pass
