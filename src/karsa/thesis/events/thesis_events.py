from dataclasses import dataclass
from typing import Optional
from karsa.thesis.domain.model.value_objects import ThesisContextSnapshot, ThesisReviewRecord

@dataclass
class ThesisProposedPayload:
    thesis: ThesisContextSnapshot

@dataclass
class ThesisActivatedPayload:
    thesis: ThesisContextSnapshot

@dataclass
class ThesisRejectedPayload:
    thesis: ThesisContextSnapshot

@dataclass
class ThesisConfidenceUpdatedPayload:
    thesis: ThesisContextSnapshot

@dataclass
class ThesisInvalidatedPayload:
    thesis: ThesisContextSnapshot

@dataclass
class ThesisRealizedPayload:
    thesis: ThesisContextSnapshot

@dataclass
class ThesisReviewedPayload:
    thesis_id: str
    review: ThesisReviewRecord
