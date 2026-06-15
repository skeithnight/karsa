from decimal import Decimal
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
