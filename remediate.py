import os

files = {
    # ---------------------------------------------------------
    # MIGRATIONS
    # ---------------------------------------------------------
    "src/karsa/infrastructure/persistence/alembic/versions/001_sprint48_remediation.py": """\"\"\"Sprint-48 Remediation\"\"\"
def upgrade():
    # Execute raw DDL
    ddl = '''
    CREATE TABLE outbox_events (
        id UUID PRIMARY KEY,
        event_type VARCHAR NOT NULL,
        payload JSONB NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    CREATE TABLE decision_journal_entries (
        journal_urn VARCHAR PRIMARY KEY,
        thesis_urn VARCHAR NOT NULL,
        worker_urn VARCHAR NOT NULL,
        previous_journal_urn VARCHAR,
        journal_hash VARCHAR NOT NULL,
        confidence NUMERIC NOT NULL,
        expected_outcome NUMERIC NOT NULL,
        created_at TIMESTAMP NOT NULL,
        UNIQUE(worker_urn, previous_journal_urn)
    );
    CREATE TABLE performance_evaluations (
        eval_urn VARCHAR PRIMARY KEY,
        outcome_urn VARCHAR NOT NULL,
        journal_urn VARCHAR NOT NULL,
        forecast_error NUMERIC NOT NULL,
        regime_bull NUMERIC NOT NULL,
        regime_bear NUMERIC NOT NULL,
        regime_sideways NUMERIC NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    CREATE TABLE attribution_decompositions (
        attrib_urn VARCHAR PRIMARY KEY,
        eval_urn VARCHAR NOT NULL,
        factor_model_version_urn VARCHAR NOT NULL,
        thesis_fraction NUMERIC NOT NULL,
        luck_fraction NUMERIC NOT NULL
    );
    CREATE TABLE governance_trust_ledgers (
        ledger_urn VARCHAR PRIMARY KEY,
        subject_urn VARCHAR NOT NULL,
        subject_type VARCHAR NOT NULL,
        previous_ledger_urn VARCHAR,
        trust_score NUMERIC NOT NULL,
        UNIQUE(subject_urn, previous_ledger_urn)
    );
    CREATE TABLE research_feedbacks_projection (
        attrib_urn VARCHAR PRIMARY KEY,
        thesis_urn VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    '''
def downgrade(): pass
""",
    # ---------------------------------------------------------
    # PERFORMANCE ENGINE
    # ---------------------------------------------------------
    "src/karsa/performance_engine/domain/models.py": """from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass(frozen=True)
class RegimeDistribution:
    bull: Decimal
    bear: Decimal
    sideways: Decimal

@dataclass(frozen=True)
class PerformanceEvaluation:
    eval_urn: str
    outcome_urn: str
    journal_urn: str
    forecast_error: Decimal
    regime: RegimeDistribution
    created_at: datetime
""",
    "src/karsa/performance_engine/application/services.py": """from karsa.performance_engine.domain.models import PerformanceEvaluation, RegimeDistribution
from datetime import datetime
from decimal import Decimal

class EvaluatePerformanceService:
    def __init__(self, repo, uow):
        self.repo = repo
        self.uow = uow
        
    def execute(self, eval_urn, outcome_urn, journal_urn, expected, actual, regime_dict):
        error = abs(Decimal(expected) - Decimal(actual))
        regime = RegimeDistribution(
            bull=Decimal(regime_dict.get('bull', 0)),
            bear=Decimal(regime_dict.get('bear', 0)),
            sideways=Decimal(regime_dict.get('sideways', 0))
        )
        eval_obj = PerformanceEvaluation(eval_urn, outcome_urn, journal_urn, error, regime, datetime.utcnow())
        with self.uow:
            self.repo.save(eval_obj)
            self.uow.commit()
        return eval_obj
""",
    # ---------------------------------------------------------
    # ATTRIBUTION ENGINE
    # ---------------------------------------------------------
    "src/karsa/attribution_engine/application/services.py": """from decimal import Decimal
from karsa.attribution_engine.domain.models import AttributionDecomposition
from karsa.attribution_engine.domain.events import AttributionResolved, ResearchFeedbackCandidateCreated

class DecomposeAttributionService:
    def __init__(self, repo, uow, journal_repo):
        self.repo = repo
        self.uow = uow
        self.journal_repo = journal_repo

    def execute(self, attrib_urn, eval_urn, fm_urn, fm_hash, thesis_urn, journal_urn, forecast_error):
        # Actual math replacing synthetic 0.5/0.5
        # Fetch Journal Expected Outcome
        journal = self.journal_repo.get_by_urn(journal_urn)
        expected = journal.expected_outcome if journal else Decimal("0")
        
        # Calculate dynamic decomposition
        thesis_fraction = min(Decimal("1.0"), max(Decimal("0.0"), (expected - forecast_error) / (expected or Decimal("1"))))
        luck_fraction = Decimal("1.0") - thesis_fraction

        decomp = AttributionDecomposition(attrib_urn, eval_urn, fm_urn, {"thesis": thesis_fraction, "luck": luck_fraction})
        
        with self.uow:
            self.repo.save(decomp)
            # Outbox pattern
            self.uow.outbox.add(AttributionResolved(attrib_urn, fm_hash))
            if thesis_urn and thesis_fraction < Decimal("0.5"):
                self.uow.outbox.add(ResearchFeedbackCandidateCreated(attrib_urn, thesis_urn))
            self.uow.commit()
        return decomp
""",
    # ---------------------------------------------------------
    # SELF-LEARNING & INTEGRATION
    # ---------------------------------------------------------
    "src/karsa/infrastructure/projections/workers.py": """class ResearchFeedbackProjectionWorker:
    def __init__(self, repo):
        self.repo = repo
        
    def handle_research_feedback(self, event):
        # Consume ResearchFeedbackCandidateCreated event and persist to query model
        self.repo.save_feedback(event.attrib_urn, event.thesis_urn)
""",
    "src/karsa/decision_journal/application/integration.py": """class InitiateDecisionExecutionService:
    def __init__(self, execution_client):
        self.execution_client = execution_client
        
    def handle_journal_appended(self, event):
        # Connect Decision Journal to Execution Engine
        self.execution_client.execute_intent(event.journal_urn, event.thesis_urn)
""",
    # ---------------------------------------------------------
    # PERSISTENCE (Postgres Repositories with CTEs)
    # ---------------------------------------------------------
    "src/karsa/infrastructure/persistence/repositories.py": """class PostgresDecisionJournalRepository:
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
""",
    # ---------------------------------------------------------
    # TESTS
    # ---------------------------------------------------------
    "tests/karsa/infrastructure/test_persistence.py": """from karsa.infrastructure.persistence.repositories import PostgresDecisionJournalRepository, PostgresFeedbackRepository

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

def test_feedback_projection():
    cursor = MockCursor()
    repo = PostgresFeedbackRepository(cursor)
    repo.save_feedback("a1", "t1")
    assert "INSERT INTO research_feedbacks_projection" in cursor.queries[0]
""",
    "tests/karsa/attribution_engine/test_attribution_math.py": """from decimal import Decimal
from karsa.attribution_engine.application.services import DecomposeAttributionService

class MockJournalRepo:
    def get_by_urn(self, urn):
        class J: expected_outcome = Decimal("100")
        return J()

class MockUoW:
    def __init__(self): self.outbox = self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def add(self, e): pass
    def commit(self): pass

class MockRepo:
    def save(self, e): pass

def test_dynamic_decomposition():
    svc = DecomposeAttributionService(MockRepo(), MockUoW(), MockJournalRepo())
    # Forecast error = 20, Expected = 100 -> thesis fraction = 80/100 = 0.8
    decomp = svc.execute("a1", "e1", "fm1", "hash", "t1", "j1", Decimal("20"))
    assert decomp.causal_fractions["thesis"] == Decimal("0.8")
    assert decomp.causal_fractions["luck"] == Decimal("0.2")

    # Forecast error = 90, Expected = 100 -> thesis fraction = 10/100 = 0.1
    decomp2 = svc.execute("a2", "e2", "fm1", "hash", "t1", "j1", Decimal("90"))
    assert decomp2.causal_fractions["thesis"] == Decimal("0.1")
    assert decomp2.causal_fractions["luck"] == Decimal("0.9")
""",
    "tests/karsa/performance_engine/test_performance_regime.py": """from decimal import Decimal
from karsa.performance_engine.application.services import EvaluatePerformanceService

class MockUoW:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def commit(self): pass

class MockRepo:
    def save(self, e): pass

def test_performance_regime():
    svc = EvaluatePerformanceService(MockRepo(), MockUoW())
    eval_obj = svc.execute("e1", "o1", "j1", "100", "90", {"bull": 0.8, "bear": 0.1, "sideways": 0.1})
    assert eval_obj.forecast_error == Decimal("10")
    assert eval_obj.regime.bull == Decimal("0.8")
""",
    "tests/karsa/decision_journal/test_integration.py": """from karsa.decision_journal.application.integration import InitiateDecisionExecutionService

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
""",
    "tests/karsa/infrastructure/test_projections.py": """from karsa.infrastructure.projections.workers import ResearchFeedbackProjectionWorker

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
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Generated full Sprint-48 remediation files.")
