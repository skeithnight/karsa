from dataclasses import dataclass

@dataclass(frozen=True)
class AttributionResolved:
    attrib_urn: str
    factor_model_hash: str

@dataclass(frozen=True)
class ResearchFeedbackCandidateCreated:
    attrib_urn: str
    thesis_urn: str

@dataclass(frozen=True)
class CapabilityFeedbackCandidateCreated:
    attrib_urn: str
    capability_urn: str
