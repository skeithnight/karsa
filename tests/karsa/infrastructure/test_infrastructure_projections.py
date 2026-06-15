from karsa.infrastructure.projections.workers import ResearchFeedbackProjectionWorker

class MockFeedbackRepo:
    def __init__(self):
        self.called = False
    def save_feedback(self, a, t):
        self.called = True

def test_projection_worker():
    class Event:
        attrib_urn = "a1"
        thesis_urn = "t1"
    repo = MockFeedbackRepo()
    worker = ResearchFeedbackProjectionWorker(repo)
    worker.handle_research_feedback(Event())
    assert repo.called
