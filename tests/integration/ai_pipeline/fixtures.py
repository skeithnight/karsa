"""Real market data fixtures for integration testing.

Contains realistic price series derived from actual market behavior:
- AAPL: Large-cap tech, moderate vol (~22% annualized)
- TSLA: High-vol meme-adjacent (~55% annualized)
- NVDA: High-growth semiconductor (~45% annualized)
- UTIL: Low-vol utility stock (~12% annualized)
- CRASH: Simulated flash crash scenario
- EARNINGS: Simulated earnings gap scenario

Price series are generated using geometric Brownian motion with
parameters calibrated to real historical behavior.
"""
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Tuple


def generate_gbm_prices(
    start_price: float,
    annualized_vol: float,
    drift: float = 0.0,
    days: int = 252,
    seed: int = 42,
) -> List[float]:
    """Generate realistic price series using Geometric Brownian Motion.

    Args:
        start_price: Starting price level.
        annualized_vol: Annualized volatility (e.g., 0.22 for 22%).
        drift: Annualized drift (e.g., 0.10 for 10% annual return).
        days: Number of trading days to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of daily close prices.
    """
    rng = random.Random(seed)
    daily_vol = annualized_vol / math.sqrt(252)
    daily_drift = drift / 252
    prices = [start_price]

    for _ in range(days - 1):
        # GBM: S_{t+1} = S_t * exp((mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
        z = rng.gauss(0, 1)
        log_return = (daily_drift - 0.5 * daily_vol ** 2) + daily_vol * z
        new_price = prices[-1] * math.exp(log_return)
        prices.append(round(new_price, 2))

    return prices


def generate_dates(start: datetime, days: int) -> List[datetime]:
    """Generate trading day timestamps (skip weekends)."""
    dates = []
    current = start
    while len(dates) < days:
        if current.weekday() < 5:  # Mon-Fri
            dates.append(current)
        current += timedelta(days=1)
    return dates


# --- AAPL: Large-cap tech, ~22% annualized vol ---
AAPL_PRICES = generate_gbm_prices(
    start_price=185.0,
    annualized_vol=0.22,
    drift=0.08,
    days=252,
    seed=42,
)

# --- TSLA: High-vol, ~55% annualized vol ---
TSLA_PRICES = generate_gbm_prices(
    start_price=245.0,
    annualized_vol=0.55,
    drift=0.15,
    days=252,
    seed=123,
)

# --- NVDA: High-growth semi, ~45% annualized vol ---
NVDA_PRICES = generate_gbm_prices(
    start_price=480.0,
    annualized_vol=0.45,
    drift=0.25,
    days=252,
    seed=456,
)

# --- UTIL: Low-vol utility, ~12% annualized vol ---
UTIL_PRICES = generate_gbm_prices(
    start_price=65.0,
    annualized_vol=0.12,
    drift=0.04,
    days=252,
    seed=789,
)


def get_crash_scenario() -> List[float]:
    """Simulate a flash crash: normal trading then -15% in 3 days."""
    normal = generate_gbm_prices(100.0, 0.20, 0.05, days=20, seed=999)
    crash = [
        normal[-1] * 0.95,   # Day 1: -5%
        normal[-1] * 0.88,   # Day 2: -7% more
        normal[-1] * 0.85,   # Day 3: -3% more (total -15%)
    ]
    recovery = generate_gbm_prices(crash[-1], 0.35, 0.20, days=10, seed=1000)
    return normal + crash + recovery


def get_earnings_gap_scenario() -> List[float]:
    """Simulate an earnings gap: flat then +8% overnight gap."""
    flat = generate_gbm_prices(150.0, 0.15, 0.0, days=15, seed=888)
    gap_up = flat[-1] * 1.08  # 8% earnings gap
    post_gap = generate_gbm_prices(gap_up, 0.30, 0.10, days=10, seed=889)
    return flat + [gap_up] + post_gap


CRASH_PRICES = get_crash_scenario()
EARNINGS_PRICES = get_earnings_gap_scenario()


def make_bar_series(
    symbol: str,
    prices: List[float],
    start_time: datetime = None,
    timeframe: str = "1d",
) -> list:
    """Convert price list to NormalizedAggregatedBar objects."""
    from karsa.providers.domain.normalization import NormalizedAggregatedBar

    if start_time is None:
        start_time = datetime(2025, 1, 2, 14, 30, tzinfo=timezone.utc)

    bars = []
    for i, price in enumerate(prices):
        ts = start_time + timedelta(days=i)
        # Simulate intraday range
        high = price * 1.005
        low = price * 0.995
        open_price = price * (1 + random.Random(i).uniform(-0.002, 0.002))
        volume = random.Random(i + 1000).randint(500_000, 5_000_000)

        bars.append(NormalizedAggregatedBar(
            symbol=symbol,
            timeframe=timeframe,
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=price,
            volume=volume,
            bar_close_utc=ts,
            source_provider="test_fixture",
        ))
    return bars


# Pre-built bar series for common test scenarios
AAPL_BARS = make_bar_series("AAPL", AAPL_PRICES)
TSLA_BARS = make_bar_series("TSLA", TSLA_PRICES)
NVDA_BARS = make_bar_series("NVDA", NVDA_PRICES)
UTIL_BARS = make_bar_series("UTIL", UTIL_PRICES)
CRASH_BARS = make_bar_series("CRASH", CRASH_PRICES)
EARNINGS_BARS = make_bar_series("EARNINGS", EARNINGS_PRICES)


# --- Realistic LLM Response Fixtures ---

LLM_THESIS_RESPONSES = {
    "valid_buy": """{
        "title": "AAPL bullish breakout above 200-day SMA",
        "ticker": "AAPL",
        "side": "BUY",
        "conviction": 0.75,
        "time_horizon": "SWING",
        "stop_loss": 190.0,
        "take_profit": 210.0,
        "position_size_pct": 2.0,
        "reasoning": "AAPL broke above 200-day SMA with volume confirmation. Institutional memory shows similar pattern in Jan 2025 yielded +8% in 5 days. RSI not yet overbought at 58."
    }""",
    "valid_sell": """{
        "title": "TSLA overextended mean reversion",
        "ticker": "TSLA",
        "side": "SELL",
        "conviction": 0.65,
        "time_horizon": "POSITION",
        "stop_loss": 280.0,
        "take_profit": 200.0,
        "position_size_pct": 1.5,
        "reasoning": "TSLA trading 3 standard deviations above 50-day mean. Post-earnings fade historically reliable. RSI > 80."
    }""",
    "hallucination": """{
        "title": "Apple acquires Microsoft for $3T",
        "ticker": "AAPL",
        "side": "BUY",
        "conviction": 0.95,
        "time_horizon": "LONG_TERM",
        "stop_loss": null,
        "take_profit": 300.0,
        "position_size_pct": 5.0,
        "reasoning": "Apple announced acquisition of Microsoft. Combined entity would dominate AI. Expecting massive synergies and 50% upside."
    }""",
    "low_conviction": """{
        "title": "NVDA unclear direction",
        "ticker": "NVDA",
        "side": "BUY",
        "conviction": 0.15,
        "time_horizon": "INTRADAY",
        "stop_loss": 470.0,
        "take_profit": 490.0,
        "position_size_pct": 0.5,
        "reasoning": "Mixed signals. Volume declining, RSI neutral at 50. Some analyst upgrades but macro headwinds."
    }""",
    "oversized": """{
        "title": "NVDA all-in conviction play",
        "ticker": "NVDA",
        "side": "BUY",
        "conviction": 0.9,
        "time_horizon": "SWING",
        "stop_loss": 460.0,
        "take_profit": 550.0,
        "position_size_pct": 8.0,
        "reasoning": "Highest conviction trade of the quarter. AI capex cycle just beginning."
    }""",
}

LLM_GOVERNANCE_RESPONSES = {
    "approve": """{
        "approved": true,
        "reasoning": "Thesis is sound. Technical setup confirmed by institutional memory. Risk/reward ratio is 2:1. Position size within limits.",
        "risk_flags": [],
        "adjusted_position_size_pct": null
    }""",
    "reject_hallucination": """{
        "approved": false,
        "reasoning": "No credible source confirms Apple-Microsoft acquisition. This claim contradicts all available market data and news sources. Classic hallucination pattern.",
        "risk_flags": ["HALLUCINATION"],
        "adjusted_position_size_pct": null
    }""",
    "reject_logic": """{
        "approved": false,
        "reasoning": "Stop loss at 280 is above entry price for a SELL position. This would trigger immediately. Take profit at 200 is reasonable but the stop loss placement is logically inconsistent.",
        "risk_flags": ["LOGICAL_INCONSISTENCY"],
        "adjusted_position_size_pct": null
    }""",
    "approve_scaled": """{
        "approved": true,
        "reasoning": "Thesis has merit but position size is aggressive for current volatility regime. Reducing from 2% to 1% of portfolio.",
        "risk_flags": [],
        "adjusted_position_size_pct": 1.0
    }""",
}

# --- RAG Context Fixtures ---

RAG_CONTEXTS = {
    "aapl_bullish": """=== INSTITUTIONAL MEMORY (RAG Context) ===
Found 3 relevant historical entries:

--- Entry 1 (similarity: 0.92) ---
Type: post_mortem_completed
Ticker: AAPL
Outcome: WIN
PnL: 4.2%
Content: AAPL broke above 200-day SMA on 2025-01-15 with above-average volume. Position entered at $185, exited at $192.80 after 5 days.

--- Entry 2 (similarity: 0.87) ---
Type: thesis_approved
Ticker: AAPL
Side: BUY
Content: Bullish thesis on AAPL based on services revenue growth and iPhone cycle. Approved with 0.7 conviction.

--- Entry 3 (similarity: 0.81) ---
Type: news_article
Ticker: AAPL
Content: Apple reports record Q1 services revenue, beating estimates by 8%.
=== END INSTITUTIONAL MEMORY ===""",
    "tsla_bearish": """=== INSTITUTIONAL MEMORY (RAG Context) ===
Found 2 relevant historical entries:

--- Entry 1 (similarity: 0.89) ---
Type: post_mortem_completed
Ticker: TSLA
Outcome: LOSS
PnL: -6.1%
Content: Shorted TSLA at 250 on overextension. Stock continued to squeeze to 265 before reverting. Stop loss triggered.

--- Entry 2 (similarity: 0.84) ---
Type: thesis_invalidated
Ticker: TSLA
Content: Bearish thesis invalidated by unexpected robotaxi announcement. Lesson: TSLA has higher event risk than vol suggests.
=== END INSTITUTIONAL MEMORY ===""",
    "empty": "",
}
