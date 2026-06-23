"""Governance Agent Service — LLM-as-a-Judge thesis validation.

Sprint-55: Consumes ThesisGeneratedEvent, validates against:
- Hallucination detection (cross-reference claims with market data/RAG)
- Logical consistency (stop-loss/take-profit math, conviction vs evidence)
- Risk limits (position size, horizon appropriateness)

Emits ThesisApprovedEvent or ThesisRejectedEvent.
Uses 'karsa-fast' model group for cost efficiency.
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from karsa.thesis.ai.domain.models import (
    TradeThesis,
    GovernanceDecision,
    RiskFlag,
    ThesisSide,
)
from karsa.thesis.ai.domain.events import (
    ThesisGeneratedEvent,
    ThesisApprovedEvent,
    ThesisRejectedEvent,
)

logger = logging.getLogger(__name__)


GOVERNANCE_SYSTEM_PROMPT = """You are a rigorous trade thesis validator for an autonomous trading firm.

Your job is to evaluate a trade thesis for:
1. HALLUCINATION: Does the thesis make claims that contradict the provided market data or institutional memory?
2. LOGICAL CONSISTENCY: Are stop-loss, take-profit, and position size mathematically sound? Does conviction match the evidence quality?
3. RISK LIMITS: Does position_size exceed 5%? Is the time horizon appropriate for the thesis?

You MUST respond with valid JSON:
{
    "approved": true or false,
    "reasoning": "Detailed explanation of your decision",
    "risk_flags": ["HALLUCINATION", "LOGICAL_INCONSISTENCY", "POSITION_SIZE_EXCEEDED", "HORIZON_MISMATCH"],
    "adjusted_position_size_pct": null or adjusted value if too high
}

Rules:
- Be SKEPTICAL. Default to rejection if evidence is weak.
- A thesis with conviction < 0.5 should rarely be approved for real money.
- "Apple acquired Microsoft" or similarly impossible claims = HALLUCINATION.
- If stop_loss is above entry for a BUY (or below for a SELL) = LOGICAL_INCONSISTENCY.
- If position_size_pct > 5.0 = POSITION_SIZE_EXCEEDED.
- If risk_flags is empty and thesis is sound, approve.
"""


class GovernanceAgentService:
    """Orchestrates the governance pipeline: thesis -> cross-reference -> LLM judgment -> emit decision.

    Consumes ThesisGeneratedEvent, validates, and emits approval/rejection.
    """

    def __init__(
        self,
        call_llm: Callable,  # async callable: (group, messages, response_format) -> dict
        retrieve_context: Optional[Callable] = None,  # async callable for RAG cross-reference
        publish_event: Optional[Callable] = None,  # async callable: (event) -> None
    ):
        self._call_llm = call_llm
        self._retrieve_context = retrieve_context
        self._publish_event = publish_event
        self._approved_count = 0
        self._rejected_count = 0

    async def validate_thesis(
        self,
        thesis: TradeThesis,
    ) -> GovernanceDecision:
        """Validate a trade thesis through the governance pipeline.

        Args:
            thesis: The TradeThesis to validate.

        Returns:
            GovernanceDecision with approval/rejection and reasoning.
        """
        # 1. Cross-reference with RAG for hallucination detection
        rag_context = ""
        if self._retrieve_context:
            try:
                rag_context = await self._retrieve_context(
                    ticker=thesis.ticker,
                    query_text=f"Recent news and price action for {thesis.ticker}",
                )
            except Exception as e:
                logger.warning(f"RAG cross-reference failed: {e}")

        # 2. Pre-LLM deterministic checks
        pre_flags = self._deterministic_checks(thesis)
        if pre_flags:
            # If deterministic checks find critical issues, reject without LLM call
            critical_flags = {RiskFlag.POSITION_SIZE_EXCEEDED}
            if pre_flags & critical_flags:
                decision = GovernanceDecision(
                    approved=False,
                    reasoning=f"Failed deterministic checks: {[f.value for f in pre_flags]}",
                    risk_flags=list(pre_flags),
                    model_used="deterministic",
                )
                await self._emit_decision(thesis, decision)
                self._rejected_count += 1
                return decision

        # 3. Construct governance prompt
        user_prompt = self._build_prompt(thesis, rag_context)

        # 4. Call LLM (karsa-fast for cost efficiency)
        try:
            result = await self._call_llm(
                model_group="karsa-fast",
                messages=[
                    {"role": "system", "content": GOVERNANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temp for consistent governance
            )
            llm_output = result.get("content", "")
            model_used = result.get("model", "unknown")
        except Exception as e:
            logger.error(f"Governance LLM call failed: {e}")
            # Fail-closed: reject on LLM failure
            decision = GovernanceDecision(
                approved=False,
                reasoning=f"Governance LLM call failed: {e}",
                risk_flags=[RiskFlag.PARSE_FAILURE],
                model_used="error",
            )
            await self._emit_decision(thesis, decision)
            self._rejected_count += 1
            return decision

        # 5. Parse decision
        decision = self._parse_decision(llm_output, model_used)

        # 6. Merge deterministic flags
        if pre_flags:
            decision.risk_flags = list(set(decision.risk_flags + list(pre_flags)))
            if not decision.approved or pre_flags:
                decision.approved = False

        # 7. Emit event
        await self._emit_decision(thesis, decision)

        if decision.approved:
            self._approved_count += 1
        else:
            self._rejected_count += 1

        logger.info(
            f"Governance decision for {thesis.ticker}: "
            f"{'APPROVED' if decision.approved else 'REJECTED'} "
            f"flags={[f.value for f in decision.risk_flags]}"
        )
        return decision

    def _deterministic_checks(self, thesis: TradeThesis) -> set:
        """Run deterministic validation checks (no LLM needed)."""
        flags = set()

        # Position size limit
        if thesis.position_size_pct > 5.0:
            flags.add(RiskFlag.POSITION_SIZE_EXCEEDED)

        # Stop-loss sanity
        if thesis.stop_loss is not None:
            if thesis.side == ThesisSide.BUY and thesis.stop_loss <= 0:
                flags.add(RiskFlag.LOGICAL_INCONSISTENCY)
            elif thesis.side == ThesisSide.SELL and thesis.stop_loss <= 0:
                flags.add(RiskFlag.LOGICAL_INCONSISTENCY)

        # Conviction vs side mismatch
        if thesis.conviction.value < 0.1 and thesis.side in (ThesisSide.BUY, ThesisSide.SELL):
            flags.add(RiskFlag.LOGICAL_INCONSISTENCY)

        return flags

    def _build_prompt(self, thesis: TradeThesis, rag_context: str) -> str:
        """Build the governance validation prompt."""
        prompt = f"=== THESIS TO VALIDATE ===\n"
        prompt += f"Ticker: {thesis.ticker}\n"
        prompt += f"Side: {thesis.side.value}\n"
        prompt += f"Conviction: {thesis.conviction.value:.2f}\n"
        prompt += f"Time Horizon: {thesis.time_horizon.value}\n"
        prompt += f"Stop Loss: {thesis.stop_loss}\n"
        prompt += f"Take Profit: {thesis.take_profit}\n"
        prompt += f"Position Size: {thesis.position_size_pct:.1f}%\n"
        prompt += f"Title: {thesis.title}\n"
        prompt += f"Reasoning: {thesis.reasoning}\n"
        prompt += f"RAG Context Used: {thesis.rag_context_used}\n"

        if rag_context:
            prompt += f"\n{rag_context}\n"

        prompt += "\n=== END THESIS ===\n"
        prompt += "\nEvaluate this thesis for hallucination, logical consistency, and risk limits."
        return prompt

    def _parse_decision(self, llm_output: str, model_used: str) -> GovernanceDecision:
        """Parse LLM output into a GovernanceDecision."""
        # Extract JSON
        data = self._extract_json(llm_output)
        if data is None:
            return GovernanceDecision(
                approved=False,
                reasoning=f"Could not parse governance response: {llm_output[:200]}",
                risk_flags=[RiskFlag.PARSE_FAILURE],
                model_used=model_used,
            )

        # Parse risk flags
        raw_flags = data.get("risk_flags", [])
        risk_flags = []
        for f in raw_flags:
            try:
                risk_flags.append(RiskFlag(f.upper()))
            except ValueError:
                pass

        # Parse adjusted position size
        adjusted_size = data.get("adjusted_position_size_pct")
        if adjusted_size is not None:
            adjusted_size = float(adjusted_size)

        return GovernanceDecision(
            approved=bool(data.get("approved", False)),
            reasoning=data.get("reasoning", ""),
            risk_flags=risk_flags,
            adjusted_position_size_pct=adjusted_size,
            model_used=model_used,
        )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM output."""
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if "\n" in part:
                    part = part.split("\n", 1)[1] if part.strip().startswith("json") else part
                part = part.strip()
                if part.startswith("{"):
                    try:
                        return json.loads(part)
                    except json.JSONDecodeError:
                        continue
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    async def _emit_decision(self, thesis: TradeThesis, decision: GovernanceDecision) -> None:
        """Emit approval or rejection event."""
        if not self._publish_event:
            return

        if decision.approved:
            event = ThesisApprovedEvent(
                thesis_id=thesis.thesis_id,
                ticker=thesis.ticker,
                side=thesis.side.value,
                conviction=thesis.conviction.value,
                time_horizon=thesis.time_horizon.value,
                stop_loss=thesis.stop_loss,
                take_profit=thesis.take_profit,
                position_size_pct=thesis.position_size_pct,
                adjusted_position_size_pct=decision.adjusted_position_size_pct,
                title=thesis.title,
                reasoning=thesis.reasoning,
                governance_reasoning=decision.reasoning,
                model_used=decision.model_used,
            )
        else:
            event = ThesisRejectedEvent(
                thesis_id=thesis.thesis_id,
                ticker=thesis.ticker,
                side=thesis.side.value,
                conviction=thesis.conviction.value,
                title=thesis.title,
                reasoning=thesis.reasoning,
                governance_reasoning=decision.reasoning,
                risk_flags=[f.value for f in decision.risk_flags],
                model_used=decision.model_used,
            )

        try:
            await self._publish_event(event)
        except Exception as e:
            logger.error(f"Failed to publish governance event: {e}")

    @property
    def approved_count(self) -> int:
        return self._approved_count

    @property
    def rejected_count(self) -> int:
        return self._rejected_count
