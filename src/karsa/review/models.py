from enum import Enum
from dataclasses import dataclass
from typing import Optional

class IssueStatus(Enum):
    OPEN = "OPEN"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"

@dataclass
class Issue:
    id: str
    severity: str
    description: str
    evidence: str
    status: IssueStatus
    cycle_introduced: int
