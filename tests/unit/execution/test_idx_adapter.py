"""Unit tests for IDX Broker Adapter.

Tests cover:
- Registration in BROKER_ADAPTER_REGISTRY via BrokerAdapterFactory
- route_order returns correct contract (broker_id, broker_order_ref, status)
- Fill log records routed orders
- Constructor accepts credentials dict + **kwargs
"""
import pytest

from karsa.execution.application.bridge_services import BrokerAdapterFactory
# Import the adapter to trigger registration
import karsa.execution.infrastructure.adapters.idx_adapter  # noqa: F401


class TestIDXAdapterRegistration:
    def test_registered_in_registry(self):
        registered = BrokerAdapterFactory.list_registered()
        assert "idx" in registered

    def test_create_via_factory(self):
        adapter = BrokerAdapterFactory.create(
            "idx",
            credentials={"api_key": "test-key", "api_secret": "test-secret"},
        )
        assert adapter.broker_id == "idx"

    def test_create_with_extra_kwargs(self):
        adapter = BrokerAdapterFactory.create(
            "idx",
            credentials={"api_key": "k", "api_secret": "s"},
            paper_trading=True,
            region="jakarta",
        )
        assert adapter.broker_id == "idx"


class TestIDXAdapterRouteOrder:
    def _make_adapter(self):
        return BrokerAdapterFactory.create(
            "idx",
            credentials={"api_key": "test", "api_secret": "test", "client_id": "c1"},
        )

    def test_route_order_returns_correct_contract(self):
        adapter = self._make_adapter()
        result = adapter.route_order(
            execution_id="exec-001",
            symbol="BBCA.JK",
            quantity=10,
            direction="BUY",
            order_type="LIMIT",
            price=9500.0,
        )
        assert "broker_id" in result
        assert "broker_order_ref" in result
        assert "status" in result
        assert result["broker_id"] == "idx"
        assert result["status"] == "SENT"
        assert result["broker_order_ref"].startswith("idx_ord_")
        assert len(result["broker_order_ref"]) == len("idx_ord_") + 12

    def test_route_order_rejects_zero_quantity(self):
        adapter = self._make_adapter()
        result = adapter.route_order(
            execution_id="exec-002",
            symbol="BBCA.JK",
            quantity=0,
            direction="BUY",
            order_type="MARKET",
        )
        assert result["status"] == "REJECTED"
        assert result["broker_order_ref"] is None
        assert "error_message" in result

    def test_route_order_rejects_negative_quantity(self):
        adapter = self._make_adapter()
        result = adapter.route_order(
            execution_id="exec-003",
            symbol="TLKM.JK",
            quantity=-5,
            direction="SELL",
            order_type="MARKET",
        )
        assert result["status"] == "REJECTED"
        assert "error_message" in result

    def test_route_order_unique_refs(self):
        adapter = self._make_adapter()
        refs = set()
        for _ in range(50):
            result = adapter.route_order(
                execution_id="exec-bulk",
                symbol="BBCA.JK",
                quantity=1,
                direction="BUY",
                order_type="MARKET",
            )
            refs.add(result["broker_order_ref"])
        assert len(refs) == 50  # All unique


class TestIDXAdapterFillLog:
    def _make_adapter(self):
        return BrokerAdapterFactory.create(
            "idx",
            credentials={"api_key": "test", "api_secret": "test"},
        )

    def test_fill_log_records_orders(self):
        adapter = self._make_adapter()
        adapter.route_order(
            execution_id="exec-100",
            symbol="BBCA.JK",
            quantity=5,
            direction="BUY",
            order_type="LIMIT",
            price=9500.0,
        )
        assert len(adapter._fill_log) == 1
        record = adapter._fill_log[0]
        assert record["execution_id"] == "exec-100"
        assert record["symbol"] == "BBCA.JK"
        assert record["lots"] == 5
        assert record["shares"] == 500  # 5 lots * 100
        assert record["direction"] == "BUY"
        assert record["order_type"] == "LIMIT"
        assert record["price"] == 9500.0
        assert record["status"] == "SENT"

    def test_fill_log_accumulates(self):
        adapter = self._make_adapter()
        for i in range(3):
            adapter.route_order(
                execution_id=f"exec-{i}",
                symbol="TLKM.JK",
                quantity=2,
                direction="SELL",
                order_type="MARKET",
            )
        assert len(adapter._fill_log) == 3
        assert adapter._fill_log[2]["execution_id"] == "exec-2"

    def test_fill_log_not_recorded_on_rejection(self):
        adapter = self._make_adapter()
        adapter.route_order(
            execution_id="exec-rej",
            symbol="BBCA.JK",
            quantity=0,
            direction="BUY",
            order_type="MARKET",
        )
        assert len(adapter._fill_log) == 0


class TestIDXAdapterConstructor:
    def test_accepts_credentials_dict(self):
        from karsa.execution.infrastructure.adapters.idx_adapter import IDXAdapter
        adapter = IDXAdapter(credentials={"api_key": "k", "api_secret": "s"})
        assert adapter.broker_id == "idx"

    def test_accepts_credentials_and_kwargs(self):
        from karsa.execution.infrastructure.adapters.idx_adapter import IDXAdapter
        adapter = IDXAdapter(
            credentials={"api_key": "k", "api_secret": "s"},
            paper_trading=True,
            custom_option="value",
        )
        assert adapter.broker_id == "idx"

    def test_default_credentials(self):
        from karsa.execution.infrastructure.adapters.idx_adapter import IDXAdapter
        adapter = IDXAdapter(credentials={})
        assert adapter.broker_id == "idx"
        assert adapter._client_id == "karsa-idx"
