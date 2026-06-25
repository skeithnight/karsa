-- Sprint-63: Realistic Investment Decision Signals
-- Creates 5 IDX trading signals with full memo data via event journal
-- Run: docker exec -i karsa-postgres-1 psql -U karsa -d karsa_db < src/karsa/seed_signals.sql

-- BBCA: BUY STRONG
INSERT INTO event_journal (id, sequence_id, stream_id, stream_version, event_type, payload, occurred_at, recorded_at, aggregate_id, aggregate_type, event_id, schema_version)
VALUES
('sig00100000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:sig-bbc-a-buy-001', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:sig:bbc-a-buy-001", "ticker": "BBCA.JK", "action": "BUY", "conviction": "STRONG", "rationale": "Bank Central Asia (BBCA) remains the gold standard in Indonesian banking. NIM expansion driven by digital banking adoption. CASA ratio at 82%. Credit growth accelerating at 12% YoY. NPL at 1.2%. ROE expected above 20% through 2027.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-22T10:00:00+00:00", "entry_price": 9275, "exit_target": 10500, "stop_loss": 8800, "position_size_pct": 2.5, "risks": ["Rising interest rate environment could compress margins", "Foreign outflow risk if Fed stays hawkish", "Regulatory changes in digital banking"], "analyst_agreement": 4}',
 NOW() - INTERVAL '2 days', NOW(), 'decision:sig-bbc-a-buy-001', 'InvestmentDecision', 'sig-bbc-a-buy-001', 1)
ON CONFLICT (event_id) DO NOTHING;

-- BBRI: BUY MEDIUM
INSERT INTO event_journal (id, sequence_id, stream_id, stream_version, event_type, payload, occurred_at, recorded_at, aggregate_id, aggregate_type, event_id, schema_version)
VALUES
('sig00200000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:sig-bbr-i-buy-002', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:sig:bbr-i-buy-002", "ticker": "BBRI.JK", "action": "BUY", "conviction": "MEDIUM", "rationale": "Bank Rakyat Indonesia is the largest SOE bank by assets. Digital transformation via BRImo app reaching 50M+ users. MSME lending segment showing strong recovery. Dividend yield attractive at 5.2%.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-23T10:00:00+00:00", "entry_price": 4120, "exit_target": 4800, "stop_loss": 3800, "position_size_pct": 1.8, "risks": ["SOE bank governance risk", "Interest rate sensitivity on MSME book", "Competition from fintech lenders"], "analyst_agreement": 3}',
 NOW() - INTERVAL '1 day', NOW(), 'decision:sig-bbr-i-buy-002', 'InvestmentDecision', 'sig-bbr-i-buy-002', 1)
ON CONFLICT (event_id) DO NOTHING;

-- TLKM: HOLD STRONG
INSERT INTO event_journal (id, sequence_id, stream_id, stream_version, event_type, payload, occurred_at, recorded_at, aggregate_id, aggregate_type, event_id, schema_version)
VALUES
('sig00300000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:sig-tlk-m-hold-003', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:sig:tlk-m-hold-003", "ticker": "TLKM.JK", "action": "HOLD", "conviction": "STRONG", "rationale": "Telkom Indonesia is the dominant telecom operator. Data center business growing 25% YoY with 12 new facilities planned. 5G rollout progressing. Subsidiary Telkomsel maintains 60% market share. Hold at current entry, fairly valued at 16x PE.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-21T10:00:00+00:00", "entry_price": 3080, "exit_target": 3500, "stop_loss": 2800, "position_size_pct": 2.0, "risks": ["5G capex could pressure free cash flow", "Starlink competition in Indonesia", "Rupiah depreciation impact on USD-denominated debt"], "analyst_agreement": 4}',
 NOW() - INTERVAL '3 days', NOW(), 'decision:sig-tlk-m-hold-003', 'InvestmentDecision', 'sig-tlk-m-hold-003', 1)
ON CONFLICT (event_id) DO NOTHING;

-- ASII: SELL WEAK
INSERT INTO event_journal (id, sequence_id, stream_id, stream_version, event_type, payload, occurred_at, recorded_at, aggregate_id, aggregate_type, event_id, schema_version)
VALUES
('sig00400000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:sig-asi-i-sell-004', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:sig:asi-i-sell-004", "ticker": "ASII.JK", "action": "SELL", "conviction": "WEAK", "rationale": "Astra International faces headwinds from declining auto sales (-8% YoY) and EV transition uncertainty. Motorcycle segment showing volume weakness. Coal mining subsidiary exposed to falling commodity prices. Recommend reducing position.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-24T06:00:00+00:00", "entry_price": 4910, "exit_target": 4500, "stop_loss": 5200, "position_size_pct": 1.0, "risks": ["Auto cycle downturn could be deeper than expected", "EV transition risk to ICE-dependent business model", "Commodity price recovery would be positive catalyst"], "analyst_agreement": 2}',
 NOW() - INTERVAL '12 hours', NOW(), 'decision:sig-asi-i-sell-004', 'InvestmentDecision', 'sig-asi-i-sell-004', 1)
ON CONFLICT (event_id) DO NOTHING;

-- BMRI: BUY MEDIUM (in risk review)
INSERT INTO event_journal (id, sequence_id, stream_id, stream_version, event_type, payload, occurred_at, recorded_at, aggregate_id, aggregate_type, event_id, schema_version)
VALUES
('sig00500000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:sig-bmr-i-buy-005', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:sig:bmr-i-buy-005", "ticker": "BMRI.JK", "action": "BUY", "conviction": "MEDIUM", "rationale": "Bank Mandiri is the largest bank by assets in Indonesia. Trade finance segment benefiting from export growth. NPL ratio improving to 1.8% from 2.5%. Digital banking investments starting to pay off with 40% cost-to-income improvement target.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-24T00:00:00+00:00", "entry_price": 5950, "exit_target": 6800, "stop_loss": 5500, "position_size_pct": 1.5, "risks": ["Trade finance exposure to global slowdown", "NPL improvement may not sustain", "Capital adequacy needs monitoring"], "analyst_agreement": 3}',
 NOW() - INTERVAL '6 hours', NOW(), 'decision:sig-bmr-i-buy-005', 'InvestmentDecision', 'sig-bmr-i-buy-005', 1)
ON CONFLICT (event_id) DO NOTHING;

-- Seed thesis snapshots with real tickers
INSERT INTO thesis_snapshots (
    thesis_urn, title, summary, rationale, confidence,
    author_urn, regime_urn, lifecycle_state, snapshot_version,
    assumptions_jsonb, created_at
) VALUES
('urn:karsa:thesis:signal:bbc-a-001', 'BBCA: Digital Banking Leader', 'Bank Central Asia positioned to benefit from Indonesia digital banking transformation. CASA ratio at 82%, lowest cost of funds among major banks.', 'Digital adoption accelerating. BBCA mobile app has 25M+ active users. NIM expansion expected to continue.', 8.0, 'ai-researcher', 'regime:stable-growth', 'ACTIVE', 1, '["Digital banking adoption continues above 30% growth", "NIM stays above 5.5% through 2027"]'::jsonb, NOW() - INTERVAL '5 days'),
('urn:karsa:thesis:signal:bbr-i-002', 'BBRI: Financial Inclusion Play', 'Bank Rakyat Indonesia largest by branch network (9,000+ branches). Primary beneficiary of financial inclusion push.', 'MSME lending recovering strongly. BRImo digital app reaching 50M users. Dividend yield 5.2% provides downside protection.', 6.0, 'ai-researcher', 'regime:stable-growth', 'ACTIVE', 1, '["MSME credit growth stays above 10%", "Digital adoption in rural areas accelerates"]'::jsonb, NOW() - INTERVAL '4 days'),
('urn:karsa:thesis:signal:tlk-m-003', 'TLKM: Data Center Growth Story', 'Telkom pivoting to data center and cloud infrastructure. 12 new facilities planned by 2026.', 'Data center revenue growing 25% YoY. 5G rollout driving data consumption.', 7.0, 'ai-researcher', 'regime:stable-growth', 'ACTIVE', 1, '["Data center demand stays strong", "5G capex stays within budget"]'::jsonb, NOW() - INTERVAL '6 days'),
('urn:karsa:thesis:signal:asi-i-004', 'ASII: Auto Cycle Concerns', 'Astra International faces headwinds from declining auto sales and EV transition uncertainty.', 'Auto sales declining 8% YoY. EV transition creates uncertainty for ICE-dependent business model.', 4.0, 'ai-researcher', 'regime:late-cycle', 'ACTIVE', 1, '["Auto sales continue declining", "EV adoption accelerates faster than expected"]'::jsonb, NOW() - INTERVAL '3 days'),
('urn:karsa:thesis:signal:bmri-005', 'BMRI: Trade Finance Recovery', 'Bank Mandiri benefits from export growth through trade finance franchise. NPL improving.', 'Trade finance segment benefiting from commodity export recovery. NPL improving to 1.8%.', 5.0, 'ai-researcher', 'regime:stable-growth', 'PROPOSED', 1, '["Export growth stays above 5%", "NPL improvement continues"]'::jsonb, NOW() - INTERVAL '2 days')
ON CONFLICT (thesis_urn) DO NOTHING;
