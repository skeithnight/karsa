"""Sprint-58: Live Risk — Volatility Targeting services.

VolatilityCalculator: Maintains rolling EWMA volatility per symbol.
RiskCalibrationEngine: Intercepts ThesisApprovedEvent, computes risk-targeted size.
Extends the existing risk/ bounded context.
"""
import asyncio
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple
import uuid

from karsa.risk.volatility_models import (
    AssetRiskMetrics,
    EWMAParameters,
    RiskTarget,
    VolatilityEstimate,
    RiskCalibrationResult,
)
from karsa.risk.volatility_events import RiskScalingAppliedEvent

logger = logging.getLogger(__name__)

# Default conservative volatility for unknown assets (50% annualized)
DEFAULT_ANNUALIZED_VOL = 0.50


class VolatilityCalculator:
    """Maintains rolling EWMA volatility estimates for tracked symbols.

    Consumes karsa.market.bar events and updates asset_risk_metrics.
    Reuses the EWMA math pattern from CovarianceForecastService.
    """

    def __init__(
        self,
        metrics_repo: Any,  # PostgresAssetRiskMetricsRepository
        params: Optional[EWMAParameters] = None,
    ):
        self._repo = metrics_repo
        self._params = params or EWMAParameters()
        # Rolling price history per symbol (last N closes for EWMA)
        self._price_history: Dict[str, List[float]] = defaultdict(list)
        # Previous EWMA variance per symbol
        self._ewma_variance: Dict[str, float] = {}
        self._update_count = 0

    def on_market_bar(
        self,
        symbol: str,
        close_price: float,
        timeframe: str = "1d",
    ) -> Optional[AssetRiskMetrics]:
        """Process a market bar and update EWMA volatility.

        Args:
            symbol: Ticker symbol.
            close_price: Bar close price.
            timeframe: Bar timeframe.

        Returns:
            Updated AssetRiskMetrics, or None if insufficient data.
        """
        if close_price <= 0:
            return None

        history = self._price_history[symbol]
        history.append(close_price)

        # Need at least 2 prices to compute a return
        if len(history) < 2:
            return None

        # Compute log return
        prev_price = history[-2]
        if prev_price <= 0:
            return None
        log_return = math.log(close_price / prev_price)

        # Update EWMA variance: var_t = lambda * var_{t-1} + (1-lambda) * r_t^2
        lam = self._params.decay_factor
        prev_var = self._ewma_variance.get(symbol, log_return ** 2)
        new_var = lam * prev_var + (1.0 - lam) * (log_return ** 2)
        self._ewma_variance[symbol] = new_var

        # Annualize: daily_vol = sqrt(var), annual_vol = daily_vol * sqrt(252)
        daily_vol = math.sqrt(new_var)
        annualized_vol = daily_vol * math.sqrt(self._params.annualization_factor)
        daily_vol_pct = daily_vol * 100.0

        # Cap history length to avoid memory growth
        if len(history) > 250:
            self._price_history[symbol] = history[-250:]
            history = self._price_history[symbol]

        # Create metrics
        metrics = AssetRiskMetrics(
            symbol=symbol,
            timeframe=timeframe,
            realized_volatility=annualized_vol,
            daily_vol_pct=daily_vol_pct,
            updated_at=datetime.now(timezone.utc),
        )

        # Persist to repo
        try:
            self._repo.upsert_metrics(metrics)
        except Exception as e:
            logger.error(f"Failed to upsert risk metrics for {symbol}: {e}")

        self._update_count += 1
        return metrics

    def get_volatility_estimate(self, symbol: str) -> VolatilityEstimate:
        """Get the current volatility estimate for a symbol.

        Falls back to repo data, then to default conservative estimate.
        """
        # Try in-memory first
        ewma_var = self._ewma_variance.get(symbol)
        if ewma_var is not None and ewma_var > 0:
            daily_vol = math.sqrt(ewma_var)
            annualized_vol = daily_vol * math.sqrt(self._params.annualization_factor)
            return VolatilityEstimate(
                symbol=symbol,
                annualized_vol=annualized_vol,
                daily_vol_pct=daily_vol * 100.0,
            )

        # Try repo
        try:
            metrics = self._repo.get_latest(symbol)
            if metrics and metrics.realized_volatility > 0:
                return VolatilityEstimate(
                    symbol=symbol,
                    annualized_vol=metrics.realized_volatility,
                    daily_vol_pct=metrics.daily_vol_pct,
                )
        except Exception as e:
            logger.warning(f"Failed to read risk metrics for {symbol}: {e}")

        # Default conservative estimate
        daily_vol = DEFAULT_ANNUALIZED_VOL / math.sqrt(self._params.annualization_factor)
        return VolatilityEstimate(
            symbol=symbol,
            annualized_vol=DEFAULT_ANNUALIZED_VOL,
            daily_vol_pct=daily_vol * 100.0,
        )

    @property
    def update_count(self) -> int:
        return self._update_count


class RiskCalibrationEngine:
    """Intercepts ThesisApprovedEvent and computes risk-targeted position size.

    Sits between AI Governance (Sprint-55) and Execution Bridge (Sprint-56).
    Every override emits RiskScalingAppliedEvent for audit.

    Fail-open: if the engine crashes, the thesis passes through unmodified.
    The Hard Risk Engine (Sprint-56) is the ultimate backstop.
    """

    def __init__(
        self,
        volatility_calculator: VolatilityCalculator,
        risk_target: Optional[RiskTarget] = None,
        portfolio_value_usd: float = 1_000_000.0,
        get_current_price: Optional[Callable] = None,  # (symbol) -> float
        publish_event: Optional[Callable] = None,
    ):
        self._vol_calc = volatility_calculator
        self._risk_target = risk_target or RiskTarget()
        self._portfolio_value = portfolio_value_usd
        self._get_price = get_current_price or (lambda s: 0.0)
        self._publish_event = publish_event
        self._calibration_count = 0
        self._override_count = 0

    async def calibrate_thesis(
        self,
        thesis_id: str,
        ticker: str,
        side: str,
        original_quantity: float,
        price: float,
        conviction: float = 1.0,
        source_event_id: str = "",
    ) -> RiskCalibrationResult:
        """Calibrate a thesis's position size based on volatility targeting.

        Formula:
            daily_vol = annualized_vol / sqrt(252)
            daily_price_vol = price * daily_vol
            risk_target_shares = target_risk_usd / daily_price_vol
            final_qty = min(risk_target_shares, original_quantity)

        If the AI's size is smaller, pass through (AI is being conservative).
        If the AI's size is larger, scale down to risk target.

        Args:
            thesis_id: URN of the thesis.
            ticker: Ticker symbol.
            side: BUY/SELL.
            original_quantity: AI-suggested quantity.
            price: Current price.
            conviction: AI conviction score (0-1).
            source_event_id: ID of the ThesisApprovedEvent.

        Returns:
            RiskCalibrationResult with calibrated quantity.
        """
        self._calibration_count += 1

        # Get volatility estimate
        vol_estimate = self._vol_calc.get_volatility_estimate(ticker)

        # Calculate risk-targeted size
        annualized_vol = vol_estimate.annualized_vol
        daily_vol = annualized_vol / math.sqrt(self._vol_calc._params.annualization_factor)
        daily_price_vol = price * daily_vol

        # Avoid division by zero
        if daily_price_vol <= 0:
            return RiskCalibrationResult(
                thesis_id=thesis_id,
                ticker=ticker,
                original_quantity=original_quantity,
                calibrated_quantity=original_quantity,
                risk_scaling_applied=False,
                target_risk_usd=self._risk_target.target_risk_per_trade_usd,
                daily_vol_pct=daily_vol * 100.0,
                daily_price_vol_usd=0.0,
                reason="Zero daily price volatility — passing through",
                volatility_estimate=vol_estimate,
            )

        risk_target_shares = self._risk_target.target_risk_per_trade_usd / daily_price_vol

        # Scale by conviction (lower conviction = smaller position)
        risk_target_shares *= conviction

        # Determine final quantity
        if original_quantity <= risk_target_shares:
            # AI is being conservative — pass through
            calibrated_qty = original_quantity
            scaling_applied = False
            reason = "AI size within risk target — no override"
        else:
            # AI is aggressive — scale down
            calibrated_qty = risk_target_shares
            scaling_applied = True
            self._override_count += 1
            reason = (
                f"Scaled down from {original_quantity:.0f} to {calibrated_qty:.0f} shares. "
                f"Risk target: ${self._risk_target.target_risk_per_trade_usd:,.0f}, "
                f"daily vol: {daily_vol*100:.2f}%, "
                f"daily price vol: ${daily_price_vol:.2f}"
            )

        result = RiskCalibrationResult(
            thesis_id=thesis_id,
            ticker=ticker,
            original_quantity=original_quantity,
            calibrated_quantity=calibrated_qty,
            risk_scaling_applied=scaling_applied,
            target_risk_usd=self._risk_target.target_risk_per_trade_usd,
            daily_vol_pct=daily_vol * 100.0,
            daily_price_vol_usd=daily_price_vol,
            reason=reason,
            volatility_estimate=vol_estimate,
        )

        # Emit audit event
        if self._publish_event:
            event = RiskScalingAppliedEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=thesis_id,
                causation_id=source_event_id,
                timestamp=datetime.now(timezone.utc),
                thesis_id=thesis_id,
                ticker=ticker,
                original_qty=original_quantity,
                calibrated_qty=calibrated_qty,
                risk_scaling_applied=scaling_applied,
                reason=reason,
                annualized_vol=annualized_vol,
                daily_vol_pct=daily_vol * 100.0,
                target_risk_usd=self._risk_target.target_risk_per_trade_usd,
            )
            try:
                await self._publish_event(event)
            except Exception as e:
                logger.error(f"Failed to publish RiskScalingAppliedEvent: {e}")

        if scaling_applied:
            logger.info(f"Risk scaling applied for {ticker}: {reason}")

        return result

    def set_portfolio_value(self, value_usd: float) -> None:
        """Update portfolio value reference."""
        self._portfolio_value = value_usd

    @property
    def calibration_count(self) -> int:
        return self._calibration_count

    @property
    def override_count(self) -> int:
        return self._override_count
