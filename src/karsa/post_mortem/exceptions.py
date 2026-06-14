from karsa.shared.infrastructure.uow import ConcurrencyConflictError

class AttributionWeightException(ValueError):
    """Raised when root cause contribution weights do not sum to exactly 1.0."""
    pass

class RecommendationStateConflictException(ValueError):
    """Raised when an invalid state transition is requested on a recommendation."""
    pass

class IncidentNotFoundException(ValueError):
    """Raised when correlation fails because the incident target is not found."""
    pass

class ImmutabilityViolationException(Exception):
    """Raised when an update or delete is attempted on an immutable ledger entry."""
    pass
