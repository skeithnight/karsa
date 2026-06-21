"""Tests for investment decision router -- Sprint-13. Wave-1G.

Covers:
- POST /investments/decisions (propose)
- POST /investments/decisions/{id}/analysts
- POST /investments/decisions/{id}/debate
- POST /investments/decisions/{id}/memo
- POST /investments/decisions/{id}/approve
- POST /investments/decisions/{id}/reject
- GET /investments/decisions/{id}
- GET /investments/decisions?ticker=BBCA
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.investment_workflow.integration.investment_workflow_command_facade import (
    CommandResult,
    InvestmentWorkflowCommandFacade,
)
from karsa.investment_workflow.integration.investment_workflow_query_facade import (
    DecisionDTO,
    InvestmentWorkflowQueryFacade,
)
from karsa.investment_workflow.transport.http.routers.investment_decision_router import (
    router,
    _get_command_facade,
    _get_query_facade,
)


def _make_client(cmd_facade=None, qry_facade=None):
    app = FastAPI()
    app.include_router(router)
    if cmd_facade:
        app.dependency_overrides[_get_command_facade] = lambda: cmd_facade
    if qry_facade:
        app.dependency_overrides[_get_query_facade] = lambda: qry_facade
    return TestClient(app, raise_server_exceptions=False)


def _valid_propose():
    return {
        "capability_family_id": "fam-001",
        "ticker": "BBCA",
        "decision_date": "2026-06-21",
        "proposed_by": "test-user",
    }


def _valid_analyst():
    return {
        "analyst_type": "FUNDAMENTAL",
        "score": 8.0,
        "confidence": 0.9,
        "output_text": "Strong fundamentals with good valuation metrics",
    }


def _valid_debate():
    return {
        "round_number": 1,
        "bull_memo": "Strong fundamentals and technicals support buy thesis at current price levels with good entry point",
        "bear_memo": "Macro headwinds and valuation concerns suggest caution at current price levels for entry",
        "bull_conviction": {"level": "STRONG", "numeric_score": 8.0, "analyst_agreement": 3},
        "bear_conviction": {"level": "WEAK", "numeric_score": 3.0, "analyst_agreement": 1},
    }


def _valid_memo():
    return {
        "ticker": "BBCA",
        "decision": "BUY",
        "conviction_level": "STRONG",
        "conviction_score": 8.0,
        "conviction_agreement": 3,
        "thesis": "BBCA offers strong dividend yield and growth potential with reasonable valuation entry point for medium term",
    }


class TestProposeDecisionEndpoint:
    """POST /investments/decisions."""

    def test_success_returns_201(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.propose_decision.return_value = CommandResult(
            success=True, message="Decision proposed",
            data={"decision_id": "d-001"},
        )
        client = _make_client(cmd_facade=cmd)

        response = client.post("/investments/decisions", json=_valid_propose())
        assert response.status_code == 201
        assert response.json()["success"] is True

    def test_facade_invoked(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.propose_decision.return_value = CommandResult(
            success=True, message="ok", data={"decision_id": "d-001"},
        )
        client = _make_client(cmd_facade=cmd)

        client.post("/investments/decisions", json=_valid_propose())
        cmd.propose_decision.assert_called_once()

    def test_missing_ticker_returns_422(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        client = _make_client(cmd_facade=cmd)

        payload = _valid_propose()
        del payload["ticker"]
        response = client.post("/investments/decisions", json=payload)
        assert response.status_code == 422


class TestRecordAnalystEndpoint:
    """POST /investments/decisions/{id}/analysts."""

    def test_success_returns_200(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.record_analyst.return_value = CommandResult(
            success=True, message="Analyst recorded",
        )
        client = _make_client(cmd_facade=cmd)

        response = client.post(
            "/investments/decisions/d-001/analysts", json=_valid_analyst()
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_invalid_score_returns_422(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        client = _make_client(cmd_facade=cmd)

        payload = _valid_analyst()
        payload["score"] = 11.0
        response = client.post(
            "/investments/decisions/d-001/analysts", json=payload
        )
        assert response.status_code == 422


class TestRecordDebateEndpoint:
    """POST /investments/decisions/{id}/debate."""

    def test_success_returns_200(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.record_debate.return_value = CommandResult(
            success=True, message="Debate recorded",
        )
        client = _make_client(cmd_facade=cmd)

        response = client.post(
            "/investments/decisions/d-001/debate", json=_valid_debate()
        )
        assert response.status_code == 200

    def test_short_memo_returns_422(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        client = _make_client(cmd_facade=cmd)

        payload = _valid_debate()
        payload["bull_memo"] = "Too short"
        response = client.post(
            "/investments/decisions/d-001/debate", json=payload
        )
        assert response.status_code == 422


class TestCreateMemoEndpoint:
    """POST /investments/decisions/{id}/memo."""

    def test_success_returns_200(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.create_memo.return_value = CommandResult(
            success=True, message="Memo created",
        )
        client = _make_client(cmd_facade=cmd)

        response = client.post(
            "/investments/decisions/d-001/memo", json=_valid_memo()
        )
        assert response.status_code == 200

    def test_invalid_decision_returns_422(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        client = _make_client(cmd_facade=cmd)

        payload = _valid_memo()
        payload["decision"] = ""  # empty string fails min_length=1
        response = client.post(
            "/investments/decisions/d-001/memo", json=payload
        )
        assert response.status_code == 422


class TestApproveRejectEndpoints:
    """POST /investments/decisions/{id}/approve and /reject."""

    def test_approve_returns_200(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.approve.return_value = CommandResult(
            success=True, message="Decision approved",
        )
        client = _make_client(cmd_facade=cmd)

        response = client.post("/investments/decisions/d-001/approve")
        assert response.status_code == 200

    def test_reject_returns_200(self):
        cmd = MagicMock(spec=InvestmentWorkflowCommandFacade)
        cmd.reject.return_value = CommandResult(
            success=True, message="Decision rejected",
        )
        client = _make_client(cmd_facade=cmd)

        response = client.post("/investments/decisions/d-001/reject")
        assert response.status_code == 200


class TestQueryEndpoints:
    """GET /investments/decisions/{id} and GET /investments/decisions."""

    def test_get_decision_returns_200(self):
        qry = MagicMock(spec=InvestmentWorkflowQueryFacade)
        qry.get_decision.return_value = DecisionDTO(
            decision_id="d-001",
            capability_family_id="fam-001",
            ticker="BBCA",
            decision_date="2026-06-21",
            state="PROPOSED",
        )
        client = _make_client(qry_facade=qry)

        response = client.get("/investments/decisions/d-001")
        assert response.status_code == 200
        assert response.json()["ticker"] == "BBCA"

    def test_get_decision_not_found(self):
        qry = MagicMock(spec=InvestmentWorkflowQueryFacade)
        qry.get_decision.return_value = None
        client = _make_client(qry_facade=qry)

        response = client.get("/investments/decisions/nonexistent")
        assert response.status_code == 404

    def test_list_decisions_by_ticker(self):
        qry = MagicMock(spec=InvestmentWorkflowQueryFacade)
        qry.get_decisions_by_ticker.return_value = [
            DecisionDTO(
                decision_id="d-001",
                capability_family_id="fam-001",
                ticker="BBCA",
                decision_date="2026-06-21",
                state="PROPOSED",
            ),
            DecisionDTO(
                decision_id="d-002",
                capability_family_id="fam-001",
                ticker="BBCA",
                decision_date="2026-06-22",
                state="APPROVED",
            ),
        ]
        client = _make_client(qry_facade=qry)

        response = client.get("/investments/decisions?ticker=BBCA")
        assert response.status_code == 200
        assert len(response.json()) == 2
