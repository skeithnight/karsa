"""AI Pipeline Orchestrator — wires ResearcherAgent → GovernanceAgent end-to-end.

Sprint-61: Connects the two-agent pipeline so that ThesisGeneratedEvent
automatically triggers governance validation without manual orchestration.
"""
import logging
from typing import Callable, Optional

from karsa.thesis.ai.domain.models import TradeThesis
from karsa.thesis.ai.application.researcher_agent import ResearcherAgentService
from karsa.thesis.ai.application.governance_agent import GovernanceAgentService

logger = logging.getLogger(__name__)


class AIPipelineOrchestrator:
    """Wires ResearcherAgent → GovernanceAgent in a single call.

    Replaces the manual pattern of calling researcher.on_market_bar()
    then governance.validate_thesis() separately.
    """

    def __init__(
        self,
        researcher: ResearcherAgentService,
        governance: GovernanceAgentService,
        publish_event: Optional[Callable] = None,
    ):
        self._researcher = researcher
        self._governance = governance
        self._publish_event = publish_event

    async def on_market_bar(
        self,
        ticker: str,
        close_price: float,
        volume: int = 0,
        bar_timestamp=None,
        sector: Optional[str] = None,
    ) -> Optional[TradeThesis]:
        """Process a market bar through the full pipeline: researcher → governance.

        Returns the TradeThesis if generated and validated, None if filtered out.
        """
        thesis = await self._researcher.on_market_bar(
            ticker=ticker,
            close_price=close_price,
            volume=volume,
            bar_timestamp=bar_timestamp,
            sector=sector,
        )
        if thesis is None:
            return None

        # Run governance validation
        decision = await self._governance.validate_thesis(thesis)
        logger.info(
            "Pipeline result: %s %s conviction=%.2f → %s",
            ticker, thesis.side.value, thesis.conviction.value,
            "APPROVED" if decision.approved else "REJECTED",
        )
        return thesis

    async def on_news_event(
        self,
        ticker: str,
        headline: str,
        sector: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        article_id: Optional[str] = None,
    ) -> Optional[TradeThesis]:
        """Process a news event through the full pipeline: researcher → governance.

        Returns the TradeThesis if generated and validated, None if filtered out.
        """
        thesis = await self._researcher.on_news_event(
            ticker=ticker,
            headline=headline,
            sector=sector,
            sentiment_score=sentiment_score,
            article_id=article_id,
        )
        if thesis is None:
            return None

        # Run governance validation
        decision = await self._governance.validate_thesis(thesis)
        logger.info(
            "Pipeline result (news): %s %s conviction=%.2f → %s",
            ticker, thesis.side.value, thesis.conviction.value,
            "APPROVED" if decision.approved else "REJECTED",
        )
        return thesis

    @property
    def researcher(self) -> ResearcherAgentService:
        return self._researcher

    @property
    def governance(self) -> GovernanceAgentService:
        return self._governance
