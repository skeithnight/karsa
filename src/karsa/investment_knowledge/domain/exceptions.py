"""Investment Knowledge domain exceptions -- Sprint-14."""


class InvalidDocumentError(Exception):
    """Raised when a research document fails validation."""


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
