from karsa.decision_journal.application.integration import InitiateDecisionExecutionService

class MockExecClient:
    def __init__(self):
        self.called = False
    def execute_intent(self, j, t):
        self.called = True

def test_decision_integration():
    class Event:
        journal_urn = "j1"
        thesis_urn = "t1"
    client = MockExecClient()
    svc = InitiateDecisionExecutionService(client)
    svc.handle_journal_appended(Event())
    assert client.called
