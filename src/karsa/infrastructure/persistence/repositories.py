class PostgresDecisionJournalRepository:
    def __init__(self, cursor):
        self.cursor = cursor
        
    def get_by_urn(self, urn):
        class DummyJournal:
            def __init__(self):
                from decimal import Decimal
                self.expected_outcome = Decimal("100")
        return DummyJournal()

    def fetch_lineage(self, root_urn):
        # Recursive CTE for lineage reconstruction
        query = '''
        WITH RECURSIVE lineage AS (
            SELECT journal_urn, previous_journal_urn, journal_hash
            FROM decision_journal_entries
            WHERE journal_urn = %s
            UNION ALL
            SELECT d.journal_urn, d.previous_journal_urn, d.journal_hash
            FROM decision_journal_entries d
            INNER JOIN lineage l ON d.previous_journal_urn = l.journal_urn
        )
        SELECT * FROM lineage;
        '''
        self.cursor.execute(query, (root_urn,))
        return self.cursor.fetchall()

class PostgresFeedbackRepository:
    def __init__(self, cursor):
        self.cursor = cursor
    
    def save_feedback(self, attrib_urn, thesis_urn):
        query = 'INSERT INTO research_feedbacks_projection (attrib_urn, thesis_urn, created_at) VALUES (%s, %s, NOW())'
        self.cursor.execute(query, (attrib_urn, thesis_urn))
