from karsa.infrastructure.persistence.repositories import PostgresDecisionJournalRepository, PostgresFeedbackRepository

class MockCursor:
    def __init__(self):
        self.queries = []
    def execute(self, query, params=None):
        self.queries.append(query)
    def fetchall(self):
        return [("j1", None, "hash1")]

def test_recursive_cte_lineage():
    cursor = MockCursor()
    repo = PostgresDecisionJournalRepository(cursor)
    res = repo.fetch_lineage("j1")
    assert "WITH RECURSIVE lineage AS" in cursor.queries[0]
    assert len(res) == 1

def test_get_by_urn():
    cursor = MockCursor()
    repo = PostgresDecisionJournalRepository(cursor)
    res = repo.get_by_urn("j1")
    assert res.expected_outcome == 100

def test_feedback_projection():
    cursor = MockCursor()
    repo = PostgresFeedbackRepository(cursor)
    repo.save_feedback("a1", "t1")
    assert "INSERT INTO research_feedbacks_projection" in cursor.queries[0]
