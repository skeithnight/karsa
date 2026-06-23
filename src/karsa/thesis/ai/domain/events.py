"""AI Agent Domain Events — Sprint-55.

Events emitted by the Researcher Agent and Governance Agent.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from karsa.shared.domain.event import DomainEvent


@dataclass
class ThesisGeneratedEvent(DomainEvent):
    """Emitted by Researcher Agent when a trade thesis is generated."""
    thesis_id: str = ""
    ticker: str = ""
    side: str = "BUY"
    conviction: float = 0.0
    time_horizon: str = "SWING"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: float = 1.0
    title: str = ""
    reasoning: str = ""
    source_market_event_id: Optional[str] = None
    source_news_event_id: Optional[str] = None
    rag_context_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "thesis_id": self.thesis_id,
            "ticker": self.ticker,
            "side": self.side,
            "conviction": self.conviction,
            "time_horizon": self.time_horizon,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size_pct": self.position_size_pct,
            "title": self.title,
            "reasoning": self.reasoning,
            "source_market_event_id": self.source_market_event_id,
            "source_news_event_id": self.source_news_event_id,
            "rag_context_used": self.rag_context_used,
        }


@dataclass
class ThesisApprovedEvent(DomainEvent):
    """Emitted by Governance Agent when a thesis passes validation."""
    thesis_id: str = ""
    ticker: str = ""
    side: str = "BUY"
    conviction: float = 0.0
    time_horizon: str = "SWING"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: float = 1.0
    title: str = ""
    reasoning: str = ""
    governance_reasoning: str = ""
    adjusted_position_size_pct: Optional[float] = None
    model_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "thesis_id": self.thesis_id,
            "ticker": self.ticker,
            "side": self.side,
            "conviction": self.conviction,
            "time_horizon": self.time_horizon,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size_pct": self.position_size_pct,
            "adjusted_position_size_pct": self.adjusted_position_size_pct,
            "title": self.title,
            "reasoning": self.reasoning,
            "governance_reasoning": self.governance_reasoning,
            "model_used": self.model_used,
        }


@dataclass
class ThesisRejectedEvent(DomainEvent):
    """Emitted by Governance Agent when a thesis fails validation."""
    thesis_id: str = ""
    ticker: str = ""
    side: str = "BUY"
    conviction: float = 0.0
    title: str = ""
    reasoning: str = ""
    governance_reasoning: str = ""
    risk_flags: List[str] = field(default_factory=list)
    model_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_name": self.event_name,
            "thesis_id": self.thesis_id,
            "ticker": self.ticker,
            "side": self.side,
            "conviction": self.conviction,
            "title": self.title,
            "reasoning": self.reasoning,
            "governance_reasoning": self.governance_reasoning,
            "risk_flags": self.risk_flags,
            "model_used": self.model_used,
        }
