from dataclasses import dataclass

@dataclass
class ThesisProposedEvent:
    thesis_urn: str
    snapshot_urn: str

@dataclass
class ThesisActivatedEvent:
    thesis_urn: str
    snapshot_urn: str

@dataclass
class ThesisChallengedEvent:
    thesis_urn: str
    challenge_urn: str

@dataclass
class ThesisRefinedEvent:
    thesis_urn: str
    transition_urn: str
    delta_manifest_hash: str

@dataclass
class ThesisInvalidatedEvent:
    thesis_urn: str

@dataclass
class ThesisRetiredEvent:
    thesis_urn: str
