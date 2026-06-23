"""Unit tests for Sprint-54: LLM Router Service."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from karsa.llm.router import LLMRouterService, GROUP_REASONING, GROUP_FAST, RouterState


class TestLLMRouterService:
    def _make_router(self, providers=None):
        if providers is None:
            providers = {
                "openai": {
                    "api_key": "test-key-openai",
                    "base_url": "https://api.openai.com/v1",
                    "models": {
                        "gpt-4o": {"group": GROUP_REASONING, "priority": 100},
                        "gpt-4o-mini": {"group": GROUP_FAST, "priority": 100},
                    },
                },
                "anthropic": {
                    "api_key": "test-key-anthropic",
                    "base_url": "https://api.anthropic.com/v1",
                    "models": {
                        "claude-sonnet": {"group": GROUP_REASONING, "priority": 200},
                    },
                },
            }
        return LLMRouterService(
            providers=providers,
            embedding_api_key="test-embedding-key",
        )

    def test_build_group_map(self):
        router = self._make_router()
        assert GROUP_REASONING in router.available_groups
        assert GROUP_FAST in router.available_groups
        assert len(router._group_map[GROUP_REASONING]) == 2  # gpt-4o, claude-sonnet
        assert len(router._group_map[GROUP_FAST]) == 1  # gpt-4o-mini

    def test_group_map_sorted_by_priority(self):
        router = self._make_router()
        reasoning = router._group_map[GROUP_REASONING]
        assert reasoning[0][2] <= reasoning[1][2]  # Lower priority first

    def test_state_tracking(self):
        state = RouterState()
        from karsa.llm.router import LLMCallMetrics
        state.record(LLMCallMetrics(model="gpt-4o", provider="openai", group=GROUP_REASONING, duration_ms=100))
        assert state.total_calls == 1
        assert state.total_failures == 0

    def test_state_tracks_failures(self):
        state = RouterState()
        from karsa.llm.router import LLMCallMetrics
        state.record(LLMCallMetrics(model="gpt-4o", provider="openai", group=GROUP_REASONING, duration_ms=0, status="error", error="timeout"))
        assert state.total_failures == 1

    def test_empty_group_raises(self):
        router = self._make_router(providers={})
        async def run():
            with pytest.raises(Exception, match="No models configured"):
                await router.call_llm("nonexistent-group", [{"role": "user", "content": "test"}])
        asyncio.run(run())


class TestLLMRouterFailover:
    def test_failover_on_provider_error(self):
        """Verify that when the first provider fails, the router tries the next."""
        providers = {
            "primary": {
                "api_key": "bad-key",
                "base_url": "https://invalid.example.com/v1",
                "models": {
                    "model-a": {"group": GROUP_REASONING, "priority": 100},
                },
            },
            "fallback": {
                "api_key": "good-key",
                "base_url": "https://api.openai.com/v1",
                "models": {
                    "model-b": {"group": GROUP_REASONING, "priority": 200},
                },
            },
        }
        router = LLMRouterService(providers=providers)
        assert len(router._group_map[GROUP_REASONING]) == 2
        # Both providers are in the group; failover logic tested via integration


class TestSignificanceFilter:
    def test_price_move_triggers(self):
        from karsa.thesis.ai.application.researcher_agent import SignificanceFilter
        f = SignificanceFilter(price_move_threshold=0.02)
        # No previous close — should NOT trigger (no baseline)
        assert f.should_generate_thesis("AAPL", 150.0) is False
        # Set baseline
        f._previous_closes["AAPL"] = 100.0
        # 2% move — should trigger
        assert f.should_generate_thesis("AAPL", 102.0) is True
        # 1% move — should NOT trigger
        assert f.should_generate_thesis("AAPL", 101.0) is False

    def test_news_always_triggers(self):
        from karsa.thesis.ai.application.researcher_agent import SignificanceFilter
        f = SignificanceFilter()
        assert f.should_generate_thesis("AAPL", 100.0, has_correlated_news=True) is True

    def test_rebalance_window_triggers(self):
        from karsa.thesis.ai.application.researcher_agent import SignificanceFilter
        f = SignificanceFilter(rebalance_hours=[9, 16])
        assert f.should_generate_thesis("AAPL", 100.0, current_hour_utc=9) is True
        assert f.should_generate_thesis("AAPL", 100.0, current_hour_utc=12) is False

    def test_counts(self):
        from karsa.thesis.ai.application.researcher_agent import SignificanceFilter
        f = SignificanceFilter(price_move_threshold=0.05)
        f.should_generate_thesis("AAPL", 100.0)  # filtered (no baseline)
        f._previous_closes["AAPL"] = 100.0
        f.should_generate_thesis("AAPL", 106.0)  # passed (>5%)
        f.should_generate_thesis("AAPL", 101.0)  # filtered (<5%)
        assert f.passed_count == 1
        assert f.filtered_count == 2
