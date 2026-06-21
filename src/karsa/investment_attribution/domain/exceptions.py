"""Investment Attribution domain exceptions -- Sprint-18."""


class InvalidAttributionError(Exception):
    """Raised when attribution data fails validation."""


class InvalidPerformanceError(Exception):
    """Raised when performance data fails validation."""


class AttributionDecompositionError(Exception):
    """Raised when attribution decomposition fails."""
