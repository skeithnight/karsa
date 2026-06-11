from typing import List
from karsa.domain.models import GovernanceDecision
from karsa.domain.persistence import EventJournalRepository
from karsa.domain.events import GovernanceDecisionEvent

class GovernanceDecisionRepository:
    def __init__(self, event_repo: EventJournalRepository):
        self.event_repo = event_repo
        
    def get_decisions(self, workflow_id: str) -> List[GovernanceDecision]:
        events = self.event_repo.load(workflow_id)
        decisions = []
        for event in events:
            if isinstance(event, GovernanceDecisionEvent):
                decisions.append(event.decision)
        return decisions
