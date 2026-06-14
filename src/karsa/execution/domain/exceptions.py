class ExecutionEngineError(Exception):
    """Base exception for all Execution Engine errors."""
    pass


class SignatureVerificationError(ExecutionEngineError):
    """Raised when CIO or Governance Exception signatures are invalid."""
    pass


class PolicyLimitExceededError(ExecutionEngineError):
    """Raised when compliance policy limits are exceeded without a valid exception token."""
    pass


class BrokerRoutingError(ExecutionEngineError):
    """Raised when routing an order to a broker fails."""
    pass


class DatabaseImmutabilityError(ExecutionEngineError):
    """Raised when attempting to update or delete records in the immutable ledger."""
    pass


class ExecutionNotFoundError(ExecutionEngineError):
    """Raised when a requested execution or ledger record cannot be found."""
    pass
