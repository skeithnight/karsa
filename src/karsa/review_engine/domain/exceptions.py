"""Review Engine domain exceptions — Sprint-10."""


class ReviewDomainError(Exception):
    """Base exception for Review Engine domain errors."""
    pass


class InvalidReviewError(ReviewDomainError):
    """Raised when a review aggregate fails validation."""
    pass


class SizeGuardrailExceededError(ReviewDomainError):
    """Raised when findings or recommendations exceed ADR-111 limits."""
    pass


class InvalidFindingError(ReviewDomainError):
    """Raised when a ReviewFinding fails validation."""
    pass


class InvalidRecommendationError(ReviewDomainError):
    """Raised when a ReviewRecommendation fails validation."""
    pass
