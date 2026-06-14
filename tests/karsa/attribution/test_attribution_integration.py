import os
import shutil
import pytest
from datetime import datetime
from decimal import Decimal
from karsa.attribution.infrastructure.repositories import (
    FileAttributionSessionRepository,
    FilePerformanceAttributionRepository
)
from karsa.attribution.application.service import (
    AttributionCalculationService,
    AttributionRecomputationService,
    AttributionInvalidationService,
    AttributionReplayService
)

def test_full_attribution_integration_flow():
    session_dir = ".karsa/test_integration/sessions/"
    record_dir = ".karsa/test_integration/records/"

    if os.path.exists(".karsa/test_integration/"):
        shutil.rmtree(".karsa/test_integration/")

    session_repo = FileAttributionSessionRepository(storage_dir=session_dir)
    record_repo = FilePerformanceAttributionRepository(storage_dir=record_dir)
    events = []

    calc_service = AttributionCalculationService(session_repo, record_repo, events)
    recalc_service = AttributionRecomputationService(session_repo, record_repo, {}, events)
    replay_service = AttributionReplayService(session_repo, record_repo)

    # 1. Stage session
    calc_service.stage_session("session-int-1", datetime(2026, 1, 1), datetime(2026, 1, 5))

    inputs_v1 = {
        "decision_id": "urn:decision:int-1",
        "thesis_urn": "urn:thesis:int-1",
        "worker_urn": "urn:worker:int-1",
        "capability_urn": "urn:capability:int-1",
        "regime_urn": "urn:regime:int-1",
        "daily_returns": [{"portfolio_return": 0.01, "benchmark_return": 0.005}],
        "daily_effects": {
            "urn:asset:int-1": [{"selection": 0.005, "allocation": 0.002, "execution": 0.001, "beta": 0.002}]
        }
    }

    # 2. Calculate and Seal
    calc_service.calculate_attribution("session-int-1", inputs_v1)
    calc_service.seal_session("session-int-1")

    records_v1 = record_repo.find_by_session("session-int-1")
    assert len(records_v1) == 1
    assert records_v1[0].attribution_version == 1
    assert records_v1[0].is_active is True

    # 3. Replay session
    replay_res = replay_service.replay_session("session-int-1", inputs_v1)
    assert replay_res["session_id"] == "session-int-1"
    assert "urn:asset:int-1" in replay_res["replayed_outputs"]

    # 4. Recomputation (V2)
    inputs_v2 = {
        "decision_id": "urn:decision:int-1",
        "thesis_urn": "urn:thesis:int-1",
        "worker_urn": "urn:worker:int-1",
        "capability_urn": "urn:capability:int-1",
        "regime_urn": "urn:regime:int-1",
        "daily_returns": [{"portfolio_return": 0.02, "benchmark_return": 0.005}],  # changed portfolio return
        "daily_effects": {
            "urn:asset:int-1": [{"selection": 0.01, "allocation": 0.002, "execution": 0.001, "beta": 0.002}]
        }
    }

    recalc_service.recompute_horizon("session-int-1", inputs_v2, "recomputation-req-int-1")

    # Verify old records are superseded/inactive
    old_records = record_repo.find_by_session("session-int-1")
    v1_rec = [r for r in old_records if r.attribution_version == 1][0]
    v2_rec = [r for r in old_records if r.attribution_version == 2][0]
    assert v1_rec.is_active is False
    assert v2_rec.is_active is True

    # Verify event logs
    superseded_events = [e for e in events if e.event_type == "AttributionSupersededEvent"]
    recomputed_events = [e for e in events if e.event_type == "AttributionRecomputedEvent"]
    assert len(superseded_events) == 1
    assert len(recomputed_events) == 1

    if os.path.exists(".karsa/test_integration/"):
        shutil.rmtree(".karsa/test_integration/")
