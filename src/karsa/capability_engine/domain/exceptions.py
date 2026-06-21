"""Capability Engine domain exceptions -- Sprint-11."""


class InvalidEvolutionError(Exception):
    """Raised when an evolution record fails domain validation."""


class InvalidHealthScoreError(Exception):
    """Raised when a health score aggregate fails domain validation."""


class InvalidEvolutionDeltaError(Exception):
    """Raised when an evolution delta fails domain validation."""


class InvalidEvolutionEvidenceError(Exception):
    """Raised when evolution evidence fails domain validation."""


class InvalidContextSnapshotError(Exception):
    """Raised when a context snapshot fails domain validation."""


class InvalidScoreComponentError(Exception):
    """Raised when a score component fails domain validation."""


class EvaluationOrderingError(Exception):
    """Raised when an evaluation sequence violates monotonic ordering. ADR-136."""


class ProjectionStalenessError(Exception):
    """Raised when source data has advanced beyond checkpoint. ADR-135."""
