"""Investment Memo domain exceptions -- Sprint-15."""


class InvalidMemoError(Exception):
    """Raised when an investment memo fails validation."""


class InvalidReturnError(Exception):
    """Raised when a realized return fails validation."""


class MemoStateError(Exception):
    """Raised when memo state transition is invalid."""


class DuplicateMemoError(Exception):
    """Raised when a duplicate memo is detected."""
