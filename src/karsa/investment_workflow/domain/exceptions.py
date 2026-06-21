"""Investment Workflow domain exceptions -- Sprint-13."""


class InvalidDecisionError(Exception):
    """Raised when an investment decision fails domain validation."""


class InvalidAnalystOutputError(Exception):
    """Raised when analyst output fails validation."""


class InvalidDebateError(Exception):
    """Raised when debate round fails validation."""


class InvalidMemoError(Exception):
    """Raised when decision memo fails validation."""


class InvalidTransitionError(Exception):
    """Raised when state transition is not allowed."""


class DuplicateAnalystError(Exception):
    """Raised when analyst output already recorded for this type."""
