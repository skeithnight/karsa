
import uuid
import json
import random
from datetime import datetime, timezone, timedelta
from karsa.bootstrap import ApplicationContainer
from karsa.post_mortem.value_objects import (
    IncidentReference,
    FailureClassification,
    RootCauseContribution,
    PostMortemFinding
)
from karsa.thesis.domain.models import Thesis
from karsa.thesis.domain.value_objects import LifecycleState
from karsa.shared.infrastructure.event_journal import EventJournalRepository
from karsa.shared.domain.event import DomainEvent

def seed():
    print("Starting Seeding Process...")
    container = ApplicationContainer()

    # ---------------------------------------------------------
    # Seed 5 CIO Decisions (IDX Target Model)
    # ---------------------------------------------------------
    print("Seeding CIO Decisions via Event Journal...")
    class PortfolioDecisionMadeEvent(DomainEvent):
        def __init__(self, decision_id, weights, desc):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"CIODecision-{decision_id}"
            self.aggregate_id = decision_id
            self.aggregate_type = "CIODecision"
            self.occurred_at = datetime.now(timezone.utc).isoformat()
            self.schema_version = 1
            self.correlation_id = decision_id
            self.causation_id = decision_id
            self.decision_id = decision_id
            self.portfolio_id = "PORT-MAIN"
            self.actor = {"actor_id": "cio-committee", "actor_type": "AGENT"}
            self.action_type = "APPROVE_ALLOCATION"
            self.payload = {"allocated_weights": weights, "votes": []}
            self.rationale = {"summary": desc, "references": []}
            self.cryptographic_signature = {"key_id": "seed", "algorithm": "Ed25519", "signature_hex": "seed"}
            self.timestamp = self.occurred_at
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ['event_id', 'stream_id', 'aggregate_id', 'aggregate_type', 'occurred_at', 'schema_version']}

    decisions = [
        {"desc": "Increase BBCA allocation", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.1, "ASII.JK": 0.2}},
        {"desc": "Reduce TLKM exposure", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.25}},
        {"desc": "Initiate ASII position", "weights": {"BBCA.JK": 0.3, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.25}},
        {"desc": "Increase cash allocation", "weights": {"BBCA.JK": 0.25, "BBRI.JK": 0.15, "BMRI.JK": 0.15, "TLKM.JK": 0.05, "ASII.JK": 0.2, "CASH": 0.2}},
        {"desc": "Rebalance banking sector", "weights": {"BBCA.JK": 0.2, "BBRI.JK": 0.2, "BMRI.JK": 0.2, "TLKM.JK": 0.05, "ASII.JK": 0.2, "CASH": 0.15}}
    ]

    for i, dec in enumerate(decisions):
        decision_id = str(uuid.uuid4())
        event = PortfolioDecisionMadeEvent(decision_id, dec["weights"], dec["desc"])
        with container.pool.connection() as conn:
            EventJournalRepository(conn).append(event, 1)
            conn.commit()

    # ---------------------------------------------------------
    # Seed 3 Post Mortems
    # ---------------------------------------------------------
    print("Seeding Post Mortems via Event Journal...")
    class PostMortemRecordCreatedEvent(DomainEvent):
        def __init__(self, pm_id, inc_ref):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"PostMortem-{pm_id}"
            self.aggregate_id = pm_id
            self.aggregate_type = "PostMortem"
            self.occurred_at = datetime.now(timezone.utc).isoformat()
            self.schema_version = 1
            self.correlation_id = pm_id
            self.causation_id = pm_id
            self.postmortem_id = pm_id
            self.incident_ref = inc_ref
            self.failure_classification = {"failure_type": "PROCESS", "severity": "HIGH", "taxonomy_version": 1}
            self.root_causes = []
            self.findings = {"timeline_events": [], "evidence_uris": []}
            self.timestamp = self.occurred_at
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ['event_id', 'stream_id', 'aggregate_id', 'aggregate_type', 'occurred_at', 'schema_version']}

    for i in range(3):
        pm_id = str(uuid.uuid4())
        inc_ref = f"urn:karsa:incident:seed:inc-{100+i}-{uuid.uuid4().hex[:8]}"
        event = PostMortemRecordCreatedEvent(pm_id, inc_ref)
        with container.pool.connection() as conn:
            EventJournalRepository(conn).append(event, 1)
            conn.commit()

    # ---------------------------------------------------------
    # Seed Portfolio Positions via Application Flow
    # ---------------------------------------------------------
    print("Seeding Portfolio Positions via Event Journal...")
    portfolio_id = "PORT-MAIN"

    class OrderFilledEvent(DomainEvent):
        def __init__(self, **kwargs):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"Portfolio-{portfolio_id}"
            self.aggregate_id = portfolio_id
            self.aggregate_type = "Portfolio"
            self.occurred_at = datetime.now(timezone.utc)
            self.schema_version = 1
            for k, v in kwargs.items():
                setattr(self, k, v)
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if k not in ['event_id', 'stream_id', 'aggregate_id', 'aggregate_type', 'occurred_at', 'schema_version']}

    with container.pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)

        journal_repo.append(OrderFilledEvent(
            causation_id=str(uuid.uuid4()), correlation_id=str(uuid.uuid4()), portfolio_id=portfolio_id, symbol="CASH", quantity=100000000.0, price=1.0, order_type="DEPOSIT", timestamp=datetime.now(timezone.utc).isoformat()
        ), 1)

        symbols = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
        for idx, sym in enumerate(symbols):
            journal_repo.append(OrderFilledEvent(
                causation_id=str(uuid.uuid4()), correlation_id=str(uuid.uuid4()), portfolio_id=portfolio_id, symbol=sym, quantity=10000.0, price=5000.0, order_type="BUY", timestamp=datetime.now(timezone.utc).isoformat()
            ), idx + 2)
        conn.commit()

    # ---------------------------------------------------------
    # Seed 3 Theses
    # ---------------------------------------------------------
    print("Seeding Theses via EventJournalRepository...")
    class ThesisProposedEvent(DomainEvent):
        def __init__(self, urn):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"Thesis-{urn}"
            self.aggregate_id = urn
            self.aggregate_type = "Thesis"
            self.occurred_at = datetime.now(timezone.utc)
            self.schema_version = 1
            self.thesis_urn = urn
        def to_dict(self):
            return {"thesis_urn": self.thesis_urn}

    with container.pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        for i in range(3):
            urn = f"urn:karsa:thesis:seed:th-{i}-{uuid.uuid4().hex[:8]}"
            journal_repo.append(ThesisProposedEvent(urn), 1)
        conn.commit()

    # ---------------------------------------------------------
    # Seed Direct Table Data (tables with no projection handler)
    # ---------------------------------------------------------
    _seed_dim_worker(container)
    _seed_portfolio_snapshots(container)
    _seed_sector_exposures(container)
    _seed_portfolio_read_valuations(container)
    _seed_post_mortem_records(container)
    _seed_worker_evaluation_records(container)
    _seed_allocation_proposals(container)
    _seed_attribution_records(container)
    _seed_investment_decision_events(container)

    print("Seed complete.")


# ---------------------------------------------------------------
# Direct table INSERTs for tables without projection workers
# ---------------------------------------------------------------

def _seed_dim_worker(container):
    """Seed 5 AI analyst workers into dim_worker."""
    print("  Seeding dim_worker...")
    now = datetime.now(timezone.utc)
    workers = [
        (1, "urn:karsa:worker:analyst-fundamental", "AGENT", now - timedelta(days=90), None, True),
        (2, "urn:karsa:worker:analyst-technical",   "AGENT", now - timedelta(days=85), None, True),
        (3, "urn:karsa:worker:analyst-macro",        "AGENT", now - timedelta(days=80), None, True),
        (4, "urn:karsa:worker:analyst-sentiment",    "AGENT", now - timedelta(days=60), None, True),
        (5, "urn:karsa:worker:analyst-quant",        "AGENT", now - timedelta(days=45), None, True),
    ]
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO dim_worker (dim_worker_id, worker_urn, subject_type, effective_from, effective_to, is_current)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (dim_worker_id) DO NOTHING
            """, workers)
        conn.commit()
    print("    -> dim_worker: 5 workers seeded")


def _seed_portfolio_snapshots(container):
    """Seed 30 days of daily equity curve data."""
    print("  Seeding portfolio_snapshots...")
    random.seed(42)
    now = datetime.now(timezone.utc)
    base_equity = 10_000_000_000.0
    equity = base_equity
    peak = base_equity
    rows = []
    for day_offset in range(30, 0, -1):
        ts = now - timedelta(days=day_offset)
        daily_return = random.uniform(-0.02, 0.03)
        daily_pnl = equity * daily_return
        equity += daily_pnl
        peak = max(peak, equity)
        dd_pct = ((peak - equity) / peak) * 100.0
        cash = equity * 0.05
        gross = equity * 1.0
        net = equity * 0.95
        realized = daily_pnl * 0.6
        unrealized = daily_pnl * 0.4
        rows.append((
            ts, round(equity, 4), round(cash, 4), round(gross, 4),
            round(net, 4), round(daily_pnl, 4), round(dd_pct, 4),
            round(realized, 4), round(unrealized, 4), 6
        ))
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO portfolio_snapshots
                    (snapshot_time, total_equity, cash_balance, gross_exposure, net_exposure,
                     daily_pnl, max_drawdown_pct, realized_pnl, unrealized_pnl, position_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, rows)
        conn.commit()
    print(f"    -> portfolio_snapshots: {len(rows)} daily rows seeded")


def _seed_sector_exposures(container):
    """Seed sector allocation breakdown at latest snapshot."""
    print("  Seeding sector_exposures...")
    now = datetime.now(timezone.utc)
    total = 10_000_000_000.0
    sectors = [
        ("Finance",        0.25, 0.23),
        ("Consumer",       0.20, 0.18),
        ("Energy",         0.15, 0.14),
        ("Technology",     0.12, 0.11),
        ("Infrastructure", 0.10, 0.09),
    ]
    rows = [(now, name, round(total * gross, 4), round(total * net, 4))
            for name, gross, net in sectors]
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO sector_exposures (snapshot_time, sector_name, gross_exposure, net_exposure)
                VALUES (%s, %s, %s, %s)
            """, rows)
        conn.commit()
    print(f"    -> sector_exposures: {len(rows)} sectors seeded")


def _seed_portfolio_read_valuations(container):
    """Seed portfolio NAV valuation."""
    print("  Seeding portfolio_read_valuations...")
    now = datetime.now(timezone.utc)
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO portfolio_read_valuations (portfolio_id, net_asset_value, cash_balance, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (portfolio_id) DO UPDATE SET
                    net_asset_value = EXCLUDED.net_asset_value,
                    cash_balance = EXCLUDED.cash_balance,
                    updated_at = EXCLUDED.updated_at
            """, ("PORT-MAIN", 10_000_000_000.0, 500_000_000.0, now))
        conn.commit()
    print("    -> portfolio_read_valuations: 1 row seeded")


def _seed_post_mortem_records(container):
    """Seed 3 post-mortem incident records."""
    print("  Seeding post_mortem_records...")
    now = datetime.now(timezone.utc)
    records = [
        {
            "postmortem_id": str(uuid.uuid4()),
            "incident_ref": f"urn:karsa:incident:seed:pm-001-{uuid.uuid4().hex[:8]}",
            "failure_classification": json.dumps({
                "failure_type": "PROCESS",
                "severity": "HIGH",
                "taxonomy_version": 1
            }),
            "root_causes": json.dumps([
                {"cause": "Stale model input data", "contribution_pct": 60},
                {"cause": "Delayed rebalance trigger", "contribution_pct": 40}
            ]),
            "findings": json.dumps({
                "thesis_urn": "urn:karsa:thesis:seed:th-0",
                "failure_reason": "Market data feed latency caused stale pricing in allocation model",
                "timeline_events": [
                    {"ts": (now - timedelta(days=10)).isoformat(), "desc": "Data feed degraded"},
                    {"ts": (now - timedelta(days=9)).isoformat(), "desc": "Rebalance skipped"}
                ],
                "evidence_uris": ["s3://karsa-evidence/pm-001/"]
            }),
            "created_at": now - timedelta(days=8)
        },
        {
            "postmortem_id": str(uuid.uuid4()),
            "incident_ref": f"urn:karsa:incident:seed:pm-002-{uuid.uuid4().hex[:8]}",
            "failure_classification": json.dumps({
                "failure_type": "MODEL",
                "severity": "MEDIUM",
                "taxonomy_version": 1
            }),
            "root_causes": json.dumps([
                {"cause": "Overfit on in-sample regime", "contribution_pct": 70},
                {"cause": "Insufficient cross-validation", "contribution_pct": 30}
            ]),
            "findings": json.dumps({
                "thesis_urn": "urn:karsa:thesis:seed:th-1",
                "failure_reason": "Volatility regime shift invalidated model assumptions",
                "timeline_events": [
                    {"ts": (now - timedelta(days=20)).isoformat(), "desc": "Regime shift detected"},
                    {"ts": (now - timedelta(days=19)).isoformat(), "desc": "Model confidence dropped"}
                ],
                "evidence_uris": ["s3://karsa-evidence/pm-002/"]
            }),
            "created_at": now - timedelta(days=18)
        },
        {
            "postmortem_id": str(uuid.uuid4()),
            "incident_ref": f"urn:karsa:incident:seed:pm-003-{uuid.uuid4().hex[:8]}",
            "failure_classification": json.dumps({
                "failure_type": "EXECUTION",
                "severity": "CRITICAL",
                "taxonomy_version": 1
            }),
            "root_causes": json.dumps([
                {"cause": "Order routing failure", "contribution_pct": 50},
                {"cause": "Slippage exceeding tolerance", "contribution_pct": 30},
                {"cause": "Insufficient pre-trade risk check", "contribution_pct": 20}
            ]),
            "findings": json.dumps({
                "thesis_urn": "urn:karsa:thesis:seed:th-2",
                "failure_reason": "Large block order hit thin market depth causing 150bps slippage",
                "timeline_events": [
                    {"ts": (now - timedelta(days=5)).isoformat(), "desc": "Order submitted"},
                    {"ts": (now - timedelta(days=5)).isoformat(), "desc": "Slippage alert triggered"},
                    {"ts": (now - timedelta(days=4)).isoformat(), "desc": "Partial fill at adverse price"}
                ],
                "evidence_uris": ["s3://karsa-evidence/pm-003/"]
            }),
            "created_at": now - timedelta(days=3)
        },
    ]
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            for rec in records:
                cur.execute("""
                    INSERT INTO post_mortem_records
                        (postmortem_id, incident_ref, failure_classification, root_causes, findings, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (postmortem_id) DO NOTHING
                """, (
                    rec["postmortem_id"], rec["incident_ref"],
                    rec["failure_classification"], rec["root_causes"],
                    rec["findings"], rec["created_at"]
                ))
        conn.commit()
    print(f"    -> post_mortem_records: {len(records)} records seeded")


def _seed_worker_evaluation_records(container):
    """Seed 10 AI analyst performance evaluations."""
    print("  Seeding worker_evaluation_records...")
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())
    worker_urns = [
        "urn:karsa:worker:analyst-fundamental",
        "urn:karsa:worker:analyst-technical",
        "urn:karsa:worker:analyst-macro",
        "urn:karsa:worker:analyst-sentiment",
        "urn:karsa:worker:analyst-quant",
    ]
    asset_urns = [
        "urn:karsa:asset:BBCA.JK",
        "urn:karsa:asset:BBRI.JK",
        "urn:karsa:asset:BMRI.JK",
        "urn:karsa:asset:TLKM.JK",
        "urn:karsa:asset:ASII.JK",
    ]
    regime_urns = [
        "urn:karsa:regime:trending",
        "urn:karsa:regime:mean-reverting",
        "urn:karsa:regime:volatile",
    ]
    random.seed(123)
    rows = []
    for i in range(10):
        record_id = str(uuid.uuid4())
        decision_id = f"urn:karsa:decision:seed:dec-{i}"
        worker_urn = worker_urns[i % len(worker_urns)]
        asset_urn = asset_urns[i % len(asset_urns)]
        regime_urn = regime_urns[i % len(regime_urns)]
        forecast_prob = round(random.uniform(0.3, 0.9), 4)
        realized_outcome = 1 if random.random() < forecast_prob else 0
        brier = round((forecast_prob - realized_outcome) ** 2, 6)
        realized_return = round(random.uniform(-0.05, 0.08), 6)
        calc_at = now - timedelta(days=30 - i)
        rows.append((
            record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
            forecast_prob, realized_outcome, brier, realized_return,
            1, True, calc_at, None, None, 1
        ))
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO worker_evaluation_records
                    (record_id, session_id, decision_id, worker_urn, asset_urn, regime_urn,
                     forecast_probability, realized_outcome, brier_score_component, realized_return,
                     evaluation_version, is_active, calculated_at,
                     superseded_by_version, invalidated_by_version, aggregate_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, rows)
        conn.commit()
    print(f"    -> worker_evaluation_records: {len(rows)} evaluations seeded")


def _seed_allocation_proposals(container):
    """Seed 3 capital allocation proposals."""
    print("  Seeding allocation_proposals...")
    now = datetime.now(timezone.utc)
    proposals = [
        {
            "proposal_id": str(uuid.uuid4()),
            "policy_id": "POL-BALANCED-001",
            "policy_snapshot": json.dumps({
                "policy_id": "POL-BALANCED-001",
                "policy_name": "Balanced Growth",
                "max_sector_concentration": 0.30,
                "min_cash_ratio": 0.05,
                "rebalance_threshold": 0.05,
                "worker_count": 5
            }),
            "journal_ref": str(uuid.uuid4()),
            "proposed_weights": json.dumps({
                "BBCA.JK": 0.25, "BBRI.JK": 0.20, "BMRI.JK": 0.15,
                "TLKM.JK": 0.10, "ASII.JK": 0.10, "CASH": 0.20
            }),
            "total_capital": 10_000_000_000.0,
            "proposal_rationale": "APPROVED - Balanced sector allocation with 20% cash buffer for Q3 rebalancing",
            "portfolio_context": json.dumps({
                "portfolio_id": "PORT-MAIN",
                "status": "APPROVED",
                "regime": "trending",
                "approved_by": "cio-committee"
            }),
            "context_hash": uuid.uuid4().hex[:64],
            "generated_at": now - timedelta(days=7)
        },
        {
            "proposal_id": str(uuid.uuid4()),
            "policy_id": "POL-AGGRESSIVE-002",
            "policy_snapshot": json.dumps({
                "policy_id": "POL-AGGRESSIVE-002",
                "policy_name": "Aggressive Alpha",
                "max_sector_concentration": 0.40,
                "min_cash_ratio": 0.02,
                "rebalance_threshold": 0.03,
                "worker_count": 5
            }),
            "journal_ref": str(uuid.uuid4()),
            "proposed_weights": json.dumps({
                "BBCA.JK": 0.30, "BBRI.JK": 0.25, "BMRI.JK": 0.20,
                "TLKM.JK": 0.15, "ASII.JK": 0.08, "CASH": 0.02
            }),
            "total_capital": 8_000_000_000.0,
            "proposal_rationale": "PENDING - Higher concentration in banking sector, awaiting risk committee approval",
            "portfolio_context": json.dumps({
                "portfolio_id": "PORT-MAIN",
                "status": "PENDING",
                "regime": "volatile",
                "awaiting_approval_from": "risk-committee"
            }),
            "context_hash": uuid.uuid4().hex[:64],
            "generated_at": now - timedelta(days=3)
        },
        {
            "proposal_id": str(uuid.uuid4()),
            "policy_id": "POL-DEFENSIVE-003",
            "policy_snapshot": json.dumps({
                "policy_id": "POL-DEFENSIVE-003",
                "policy_name": "Defensive Income",
                "max_sector_concentration": 0.25,
                "min_cash_ratio": 0.15,
                "rebalance_threshold": 0.08,
                "worker_count": 3
            }),
            "journal_ref": str(uuid.uuid4()),
            "proposed_weights": json.dumps({
                "BBCA.JK": 0.20, "BBRI.JK": 0.15, "BMRI.JK": 0.15,
                "TLKM.JK": 0.10, "ASII.JK": 0.10, "CASH": 0.30
            }),
            "total_capital": 5_000_000_000.0,
            "proposal_rationale": "REJECTED - Excessive cash allocation not justified by current regime analysis",
            "portfolio_context": json.dumps({
                "portfolio_id": "PORT-MAIN",
                "status": "REJECTED",
                "regime": "mean-reverting",
                "rejected_by": "cio-committee",
                "rejection_reason": "Cash allocation exceeds regime-adjusted threshold"
            }),
            "context_hash": uuid.uuid4().hex[:64],
            "generated_at": now - timedelta(days=1)
        },
    ]
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            for p in proposals:
                cur.execute("""
                    INSERT INTO allocation_proposals
                        (proposal_id, policy_id, policy_snapshot, journal_ref, proposed_weights,
                         total_capital, proposal_rationale, portfolio_context, context_hash, generated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (proposal_id) DO NOTHING
                """, (
                    p["proposal_id"], p["policy_id"], p["policy_snapshot"],
                    p["journal_ref"], p["proposed_weights"], p["total_capital"],
                    p["proposal_rationale"], p["portfolio_context"],
                    p["context_hash"], p["generated_at"]
                ))
        conn.commit()
    print(f"    -> allocation_proposals: {len(proposals)} proposals seeded")


def _seed_attribution_records(container):
    """Seed 5 Brinson-style attribution records."""
    print("  Seeding attribution_records...")
    now = datetime.now(timezone.utc)
    tickers = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
    rows = []
    for i, ticker in enumerate(tickers):
        attr_id = str(uuid.uuid4())
        eval_id = str(uuid.uuid4())
        dec_id = str(uuid.uuid4())
        selection = round(random.uniform(-50, 120), 2)
        allocation = round(random.uniform(-30, 60), 2)
        interaction = round(random.uniform(-20, 30), 2)
        total_bps = selection + allocation + interaction
        expected = round(random.uniform(20, 80), 2)
        variance = round(random.uniform(10, 50), 2)
        rows.append((
            attr_id,
            eval_id,
            "brinson-v1",
            dec_id,
            30,
            f"urn:karsa:asset:{ticker}",
            "PORTFOLIO",
            round(total_bps, 4),
            expected,
            variance,
            json.dumps([{
                "asset_urn": f"urn:karsa:asset:{ticker}",
                "weight_pct": round(random.uniform(5, 30), 2),
                "selection_effect_bps": selection,
                "allocation_effect_bps": allocation,
                "interaction_effect_bps": interaction
            }]),
            json.dumps({
                "total_active_return_bps": round(total_bps, 2),
                "benchmark_return_bps": expected,
                "selection_total_bps": selection,
                "allocation_total_bps": allocation
            }),
            json.dumps({
                "completeness_score": round(random.uniform(0.85, 0.99), 2),
                "residual_bps": round(random.uniform(0, 5), 2),
                "data_quality": "GOOD"
            }),
            json.dumps({"source": "seed-data", "version": "1.0"}),
            json.dumps({
                "portfolio_id": "PORT-MAIN",
                "benchmark": "IDX-30",
                "evaluation_date": (now - timedelta(days=i)).date().isoformat()
            }),
            str(uuid.uuid4()),
            now - timedelta(days=i),
            "attribution-engine",
            now - timedelta(days=i)
        ))
    with container.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO attribution_records
                    (attribution_id, evaluation_id, algorithm_version, decision_id,
                     evaluation_horizon_days, target_urn, target_type,
                     total_realized_return_bps, total_expected_return_bps, total_variance_bps,
                     contributions, attribution_summary, attribution_quality,
                     quality_provenance, context_snapshot, source_request_id,
                     attributed_at, attributed_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, rows)
        conn.commit()
    print(f"    -> attribution_records: {len(rows)} records seeded")


def _seed_investment_decision_events(container):
    """Seed 5 investment decision events via event journal."""
    print("  Seeding investment decision events...")

    class InvestmentDecisionCreatedEvent(DomainEvent):
        def __init__(self, decision_id, ticker, action, conviction, rationale):
            super().__init__()
            self.event_id = str(uuid.uuid4())
            self.stream_id = f"InvestmentDecision-{decision_id}"
            self.aggregate_id = decision_id
            self.aggregate_type = "InvestmentDecision"
            self.occurred_at = datetime.now(timezone.utc).isoformat()
            self.schema_version = 1
            self.decision_id = decision_id
            self.ticker = ticker
            self.action = action
            self.conviction = conviction
            self.rationale = rationale
            self.proposed_by = "seed-data"
            self.proposed_at = self.occurred_at
        def to_dict(self):
            return {
                "decision_id": self.decision_id,
                "ticker": self.ticker,
                "action": self.action,
                "conviction": self.conviction,
                "rationale": self.rationale,
                "proposed_by": self.proposed_by,
                "proposed_at": self.proposed_at,
            }

    decisions = [
        {"ticker": "BBCA.JK", "action": "BUY",  "conviction": "HIGH",   "rationale": "Strong NIM expansion and digital banking leadership"},
        {"ticker": "BBRI.JK", "action": "BUY",  "conviction": "MEDIUM", "rationale": "SME lending growth offset by rising credit cost"},
        {"ticker": "BMRI.JK", "action": "HOLD", "conviction": "MEDIUM", "rationale": "Valuation fair; wait for CASA ratio improvement"},
        {"ticker": "TLKM.JK", "action": "SELL", "conviction": "HIGH",   "rationale": "Telkomsel ARPU erosion and 5G capex overhang"},
        {"ticker": "ASII.JK", "action": "BUY",  "conviction": "LOW",    "rationale": "Auto recovery play but margin pressure from EV transition"},
    ]

    with container.pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        for i, dec in enumerate(decisions):
            dec_id = str(uuid.uuid4())
            event = InvestmentDecisionCreatedEvent(
                dec_id, dec["ticker"], dec["action"],
                dec["conviction"], dec["rationale"]
            )
            journal_repo.append(event, i + 1)
        conn.commit()
    print(f"    -> investment decisions: {len(decisions)} events written")


if __name__ == "__main__":
    seed()
