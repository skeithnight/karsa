from dataclasses import dataclass

@dataclass(frozen=True)
class Provenance:
    """Immutable value object representing the origin of a decision or fact."""
    urn: str
    
    def validate(self):
        if not self.urn:
            raise ValueError("urn is required")
        if not self.urn.startswith("urn:"):
            raise ValueError("urn must start with 'urn:'")
