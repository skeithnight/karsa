"""Investment Governance domain exceptions -- Sprint-17."""


class MandateViolationError(Exception):
    """Raised when a mandate rule is violated."""


class InvalidMandateError(Exception):
    """Raised when mandate configuration is invalid."""


class ComplianceCheckError(Exception):
    """Raised when compliance check fails."""
