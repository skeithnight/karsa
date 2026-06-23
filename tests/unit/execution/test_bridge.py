"""Unit tests for Sprint-56/57: Execution Bridge.

Tests cover:
- Hard Risk Engine (max order, position size, daily turnover)
- Order Slicer (TWAP logic)
- Kill Switch
- Broker Adapter Factory
- Execution Feedback Loop
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from karsa.execution.domain.bridge_models import (
    ExecutionOrder,
    ExecutionFill,
    OrderSide,
    OrderType,
    OrderStatus,
    RiskLimitType,
    RiskLimit,
    RiskRejection,
    TWAPPlan,
)
from karsa.execution.application.risk_engine import HardRiskEngine
from karsa.execution.application.order_slicer import OrderSlicer
from karsa.execution.application.bridge_services import (
    OrderManagementSystem,
    BrokerAdapterFactory,
    ExecutionFeedbackLoop,
    KillSwitchService,
    BROKER_ADAPTER_REGISTRY,
)
# Import adapters to register them
import karsa.execution.infrastructure.adapters.alpaca_adapter  # noqa: F401
import karsa.execution.infrastructure.adapters.ibkr_adapter  # noqa: F401


# ============================================================
# Hard Risk Engine Tests
# ============================================================

class TestHardRiskEngine:
    def _make_engine(self, portfolio_value=1_000_000, position_value=0, daily_turnover=0):
        return HardRiskEngine(
            portfolio_value_usd=portfolio_value,
            get_position_value=lambda s: position_value,
            get_daily_turnover=lambda: daily_turnover,
        )

    def test_approve_normal_order(self):
        engine = self._make_engine()
        order = ExecutionOrder(
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=100,
            limit_price=195.0,
        )
        approved, rejection = engine.validate_order(order, estimated_price=195.0)
        assert approved is True
        assert rejection is None

    def test_reject_max_single_order(self):
        engine = self._make_engine()
        order = ExecutionOrder(
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=10000,  # $1.95M > $500k limit
            limit_price=195.0,
        )
        approved, rejection = engine.validate_order(order, estimated_price=195.0)
        assert approved is False
        assert rejection.limit_type == RiskLimitType.MAX_SINGLE_ORDER_USD

    def test_reject_position_size(self):
        engine = self._make_engine(portfolio_value=100_000, position_value=4_000)
        order = ExecutionOrder(
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=200,  # $39k + $4k = $43k > 5% of $100k
            limit_price=195.0,
        )
        approved, rejection = engine.validate_order(order, estimated_price=195.0)
        assert approved is False
        assert rejection.limit_type == RiskLimitType.MAX_POSITION_SIZE_PCT

    def test_reject_daily_turnover(self):
        # Use high portfolio value so position size check passes
        engine = self._make_engine(portfolio_value=100_000_000, daily_turnover=4_900_000)
        order = ExecutionOrder(
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=1000,  # $195k + $4.9M > $5M limit
            limit_price=195.0,
        )
        approved, rejection = engine.validate_order(order, estimated_price=195.0)
        assert approved is False
        assert rejection.limit_type == RiskLimitType.MAX_DAILY_TURNOVER_USD

    def test_update_limit(self):
        engine = self._make_engine(portfolio_value=100_000_000)
        engine.update_limit(RiskLimitType.MAX_SINGLE_ORDER_USD, 1_000_000)
        order = ExecutionOrder(
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=5000, limit_price=195.0,
        )
        approved, _ = engine.validate_order(order, estimated_price=195.0)
        assert approved is True  # $975k < $1M new limit

    def test_counts(self):
        engine = self._make_engine()
        order_ok = ExecutionOrder(symbol="X", side=OrderSide.BUY, target_quantity=10, limit_price=100)
        order_bad = ExecutionOrder(symbol="X", side=OrderSide.BUY, target_quantity=10000, limit_price=100)
        engine.validate_order(order_ok, 100)
        engine.validate_order(order_bad, 100)
        assert engine.approved_count == 1
        assert engine.rejected_count == 1


# ============================================================
# Order Slicer Tests
# ============================================================

class TestOrderSlicer:
    def test_small_order_not_sliced(self):
        slicer = OrderSlicer(twap_threshold_usd=50_000)
        order = ExecutionOrder(
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=100, limit_price=195.0,
        )
        assert slicer.should_slice(order, estimated_price=195.0) is False

    def test_large_order_sliced(self):
        slicer = OrderSlicer(twap_threshold_usd=50_000)
        order = ExecutionOrder(
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=500, limit_price=195.0,  # $97.5k
        )
        assert slicer.should_slice(order, estimated_price=195.0) is True

    def test_twap_plan_creates_slices(self):
        slicer = OrderSlicer(interval_minutes=5, duration_minutes=30)
        order = ExecutionOrder(
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=600, limit_price=195.0,
        )
        plan = slicer.create_twap_plan(order, estimated_price=195.0)
        assert plan.slice_count == 6  # 30 / 5 = 6 slices
        assert abs(sum(s.quantity for s in plan.slices) - 600) < 0.01

    def test_child_orders_created(self):
        slicer = OrderSlicer(interval_minutes=5, duration_minutes=30)
        parent = ExecutionOrder(
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=600, limit_price=195.0,
            thesis_id="urn:karsa:thesis:test",
        )
        plan = slicer.create_twap_plan(parent, estimated_price=195.0)
        children = slicer.create_child_orders(parent, plan)
        assert len(children) == 6
        for child in children:
            assert child.is_twap_child is True
            assert child.parent_order_id == parent.order_id
            assert child.thesis_id == parent.thesis_id

    def test_market_hours_skip_weekend(self):
        slicer = OrderSlicer(interval_minutes=5, duration_minutes=30)
        order = ExecutionOrder(
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=600, limit_price=195.0,
        )
        # Saturday at 10 AM UTC
        saturday = datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc)
        plan = slicer.create_twap_plan(order, estimated_price=195.0, start_time=saturday)
        # All slices should be skipped (weekend), fallback to single
        assert plan.slice_count == 1


# ============================================================
# Order Management System Tests
# ============================================================

class TestOrderManagementSystem:
    def _make_oms(self, kill_switch=False):
        risk_engine = HardRiskEngine(portfolio_value_usd=1_000_000)
        slicer = OrderSlicer(twap_threshold_usd=50_000)
        mock_repo = MagicMock()
        mock_repo.save = MagicMock()
        mock_repo.find_by_thesis_id = MagicMock(return_value=None)
        mock_publish = AsyncMock()
        oms = OrderManagementSystem(
            risk_engine=risk_engine,
            order_slicer=slicer,
            order_repo=mock_repo,
            publish_event=mock_publish,
        )
        if kill_switch:
            oms.activate_kill_switch()
        return oms, mock_repo, mock_publish

    def test_process_approved_thesis(self):
        oms, mock_repo, mock_pub = self._make_oms()
        async def run():
            order = await oms.process_approved_thesis(
                thesis_id="urn:karsa:thesis:test-1",
                ticker="AAPL",
                side="BUY",
                quantity=100,
                price=195.0,
            )
            assert order is not None
            assert order.status == OrderStatus.SUBMITTED
            mock_repo.save.assert_called()
        asyncio.run(run())

    def test_risk_rejected(self):
        oms, _, mock_pub = self._make_oms()
        async def run():
            order = await oms.process_approved_thesis(
                thesis_id="urn:karsa:thesis:test-2",
                ticker="AAPL",
                side="BUY",
                quantity=10000,  # $1.95M > $500k limit
                price=195.0,
            )
            assert order.status == OrderStatus.RISK_REJECTED
        asyncio.run(run())

    def test_kill_switch_rejects(self):
        oms, _, _ = self._make_oms(kill_switch=True)
        async def run():
            order = await oms.process_approved_thesis(
                thesis_id="urn:karsa:thesis:test-3",
                ticker="AAPL", side="BUY", quantity=100, price=195.0,
            )
            assert order is None
        asyncio.run(run())

    def test_idempotency(self):
        oms, _, _ = self._make_oms()
        async def run():
            o1 = await oms.process_approved_thesis(
                thesis_id="urn:karsa:thesis:dup", ticker="AAPL",
                side="BUY", quantity=100, price=195.0,
            )
            o2 = await oms.process_approved_thesis(
                thesis_id="urn:karsa:thesis:dup", ticker="AAPL",
                side="BUY", quantity=100, price=195.0,
            )
            assert o1 is not None
            assert o2 is None  # Duplicate skipped
        asyncio.run(run())


# ============================================================
# Broker Adapter Factory Tests
# ============================================================

class TestBrokerAdapterFactory:
    def test_list_registered(self):
        registered = BrokerAdapterFactory.list_registered()
        assert "alpaca" in registered
        assert "ibkr" in registered

    def test_create_alpaca(self):
        adapter = BrokerAdapterFactory.create(
            "alpaca",
            credentials={"api_key": "test", "api_secret": "test"},
            paper_trading=True,
        )
        assert adapter.broker_id == "alpaca"

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="No broker adapter"):
            BrokerAdapterFactory.create("unknown_broker", credentials={})


# ============================================================
# Execution Feedback Loop Tests
# ============================================================

class TestExecutionFeedbackLoop:
    def test_on_fill_report(self):
        mock_repo = MagicMock()
        order = ExecutionOrder(
            order_id="urn:karsa:execution:order:test",
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=100, status=OrderStatus.SUBMITTED,
        )
        mock_repo.find_by_broker_order_id = MagicMock(return_value=order)
        mock_repo.save = MagicMock()
        mock_repo.save_fill = MagicMock()

        loop = ExecutionFeedbackLoop(order_repo=mock_repo, fill_repo=MagicMock())
        async def run():
            fill = await loop.on_fill_report(
                broker_order_id="brk-123",
                broker_fill_id="fill-1",
                quantity=100,
                fill_price=195.50,
            )
            assert fill is not None
            assert order.filled_quantity == 100
            assert order.status == OrderStatus.FILLED
        asyncio.run(run())

    def test_partial_fill(self):
        mock_repo = MagicMock()
        order = ExecutionOrder(
            order_id="urn:karsa:execution:order:partial",
            symbol="AAPL", side=OrderSide.BUY,
            target_quantity=200, status=OrderStatus.SUBMITTED,
        )
        mock_repo.find_by_broker_order_id = MagicMock(return_value=order)
        mock_repo.save = MagicMock()
        mock_repo.save_fill = MagicMock()

        loop = ExecutionFeedbackLoop(order_repo=mock_repo, fill_repo=MagicMock())
        async def run():
            await loop.on_fill_report("brk-1", "f1", 100, 195.0)
            assert order.filled_quantity == 100
            assert order.status == OrderStatus.PARTIALLY_FILLED

            await loop.on_fill_report("brk-1", "f2", 100, 195.5)
            assert order.filled_quantity == 200
            assert order.status == OrderStatus.FILLED
        asyncio.run(run())
