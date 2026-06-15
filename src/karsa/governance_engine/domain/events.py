from dataclasses import dataclass

@dataclass(frozen=True)
class GovernanceActionExecuted:
    subject_urn: str
    action_type: str
