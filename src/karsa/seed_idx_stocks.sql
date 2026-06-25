-- Sprint-63: Seed All IDX LQ45 Stocks
-- Run: docker exec -i karsa-postgres-1 psql -U karsa -d karsa_db < src/karsa/seed_idx_stocks.sql

-- Insert IDX LQ45 universe
INSERT INTO market_universes (universe_id, name, description, members_json, created_at, updated_at)
VALUES ('idx-lq45', 'IDX LQ45', 'Index LQ45 - 45 most liquid IDX stocks', '[]'::json, NOW(), NOW())
ON CONFLICT (universe_id) DO NOTHING;

-- Insert universe members
INSERT INTO universe_members (universe_id, member_id, member_name, sector, weight_pct, added_at)
VALUES
('idx-lq45', 'BBCA.JK', 'Bank Central Asia', 'Finance', 8.5, NOW()),
('idx-lq45', 'BBRI.JK', 'Bank Rakyat Indonesia', 'Finance', 6.2, NOW()),
('idx-lq45', 'BMRI.JK', 'Bank Mandiri', 'Finance', 5.8, NOW()),
('idx-lq45', 'BBNI.JK', 'Bank Negara Indonesia', 'Finance', 3.2, NOW()),
('idx-lq45', 'TLKM.JK', 'Telkom Indonesia', 'Telecom', 5.5, NOW()),
('idx-lq45', 'ASII.JK', 'Astra International', 'Industrials', 4.8, NOW()),
('idx-lq45', 'UNVR.JK', 'Unilever Indonesia', 'Consumer', 3.5, NOW()),
('idx-lq45', 'HMSP.JK', 'HM Sampoerna', 'Consumer', 3.2, NOW()),
('idx-lq45', 'GGRM.JK', 'Gudang Garam', 'Consumer', 2.8, NOW()),
('idx-lq45', 'KLBF.JK', 'Kalbe Farma', 'Healthcare', 2.1, NOW()),
('idx-lq45', 'ICBP.JK', 'Indofood CBP', 'Consumer', 2.0, NOW()),
('idx-lq45', 'INDF.JK', 'Indofood Sukses', 'Consumer', 1.8, NOW()),
('idx-lq45', 'TOWR.JK', 'Tower Bersama', 'Telecom', 1.9, NOW()),
('idx-lq45', 'EXCL.JK', 'XL Axiata', 'Telecom', 1.5, NOW()),
('idx-lq45', 'ISAT.JK', 'Indosat Ooredoo', 'Telecom', 1.2, NOW()),
('idx-lq45', 'ANTM.JK', 'Aneka Tambang', 'Mining', 1.8, NOW()),
('idx-lq45', 'PTBA.JK', 'Bukit Asam', 'Mining', 1.5, NOW()),
('idx-lq45', 'ADRO.JK', 'Adaro Energy', 'Energy', 1.4, NOW()),
('idx-lq45', 'PTPP.JK', 'PP Presisi', 'Infrastructure', 1.2, NOW()),
('idx-lq45', 'WSKT.JK', 'Waskita Karya', 'Infrastructure', 0.8, NOW()),
('idx-lq45', 'WIKA.JK', 'Wijaya Karya', 'Infrastructure', 0.7, NOW()),
('idx-lq45', 'CPIN.JK', 'Charoen Pokphand', 'Consumer', 1.6, NOW()),
('idx-lq45', 'HEAL.JK', 'Siloam Hospitals', 'Healthcare', 1.1, NOW()),
('idx-lq45', 'MDKA.JK', 'Merdeka Battery', 'Mining', 1.0, NOW()),
('idx-lq45', 'ERAA.JK', 'Erajaya Swasembada', 'Technology', 0.9, NOW()),
('idx-lq45', 'GOTO.JK', 'GoTo Gojek Tokopedia', 'Technology', 2.5, NOW()),
('idx-lq45', 'BUKA.JK', 'Bukalapak.com', 'Technology', 0.6, NOW()),
('idx-lq45', 'EMTK.JK', 'Elang Mahkota Teknologi', 'Technology', 0.8, NOW()),
('idx-lq45', 'MTEL.JK', 'Dayamitra Telekomunikasi', 'Telecom', 1.0, NOW()),
('idx-lq45', 'PGAS.JK', 'Perusahaan Gas Negara', 'Energy', 1.1, NOW()),
('idx-lq45', 'AKRA.JK', 'AKR Corporindo', 'Energy', 0.9, NOW()),
('idx-lq45', 'TRIO.JK', 'Trimegah Sekuritas', 'Finance', 0.5, NOW()),
('idx-lq45', 'ARTO.JK', 'Bank Jago', 'Finance', 1.2, NOW()),
('idx-lq45', 'BNGA.JK', 'Bank CIMB Niaga', 'Finance', 1.0, NOW()),
('idx-lq45', 'MEGA.JK', 'Bank Mega', 'Finance', 0.7, NOW()),
('idx-lq45', 'MNCN.JK', 'MNC Capital', 'Technology', 0.4, NOW()),
('idx-lq45', 'DCII.JK', 'DCI Indonesia', 'Technology', 0.5, NOW()),
('idx-lq45', 'SMGR.JK', 'Semen Indonesia', 'Infrastructure', 0.8, NOW()),
('idx-lq45', 'INTP.JK', 'Indocement Tunggal', 'Infrastructure', 0.7, NOW()),
('idx-lq45', 'TPIA.JK', 'Chandra Asri Petrochemical', 'Basic Materials', 1.3, NOW()),
('idx-lq45', 'BRPT.JK', 'Barito Pacific', 'Basic Materials', 0.6, NOW()),
('idx-lq45', 'INKP.JK', 'Indah Kiat Pulp & Paper', 'Basic Materials', 0.9, NOW()),
('idx-lq45', 'TPMA.JK', 'Trans Power Marine', 'Industrials', 0.4, NOW()),
('idx-lq45', 'SIMA.JK', 'Sumi Indo Agro', 'Consumer', 0.3, NOW()),
('idx-lq45', 'JSMR.JK', 'Jasa Marga', 'Infrastructure', 1.4, NOW())
ON CONFLICT (universe_id, member_id) DO NOTHING;

-- Seed additional investment decisions
INSERT INTO event_journal (id, sequence_id, stream_id, stream_version, event_type, payload, occurred_at, recorded_at, aggregate_id, aggregate_type, event_id, schema_version)
VALUES
('idx00100000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:idx-antm-buy-006', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:idx:antm-buy-006", "ticker": "ANTM.JK", "action": "BUY", "conviction": "MEDIUM", "rationale": "Aneka Tambang benefits from rising nickel demand for EV batteries. Gold mining segment provides commodity hedge. Government divestment plan adds catalyst.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-23T08:00:00+00:00", "entry_price": 1510, "exit_target": 1800, "stop_loss": 1350, "position_size_pct": 1.5, "risks": ["Nickel price volatility", "Government regulatory changes", "Environmental compliance costs"], "analyst_agreement": 3}',
 NOW() - INTERVAL '1 day', NOW(), 'decision:idx-antm-buy-006', 'InvestmentDecision', 'idx-antm-buy-006', 1),
('idx00200000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:idx-goto-buy-007', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:idx:goto-buy-007", "ticker": "GOTO.JK", "action": "BUY", "conviction": "MEDIUM", "rationale": "GoTo group showing path to profitability. E-commerce and fintech segments growing. Ride-hailing market leader in Indonesia.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-22T14:00:00+00:00", "entry_price": 65, "exit_target": 85, "stop_loss": 52, "position_size_pct": 1.0, "risks": ["Profitability timeline uncertainty", "Competition from Grab", "Regulatory risk"], "analyst_agreement": 2}',
 NOW() - INTERVAL '2 days', NOW(), 'decision:idx-goto-buy-007', 'InvestmentDecision', 'idx-goto-buy-007', 1),
('idx00300000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:idx-adro-sell-008', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:idx:adro-sell-008", "ticker": "ADRO.JK", "action": "SELL", "conviction": "WEAK", "rationale": "Adaro Energy faces coal price headwinds. Transition to green energy creates long-term uncertainty. Recommend reducing position.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-24T04:00:00+00:00", "entry_price": 2850, "exit_target": 2500, "stop_loss": 3100, "position_size_pct": 0.8, "risks": ["Coal price recovery risk", "ESG divestment pressure", "Government royalty changes"], "analyst_agreement": 2}',
 NOW() - INTERVAL '8 hours', NOW(), 'decision:idx-adro-sell-008', 'InvestmentDecision', 'idx-adro-sell-008', 1),
('idx00400000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:idx-towr-hold-009', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:idx:towr-hold-009", "ticker": "TOWR.JK", "action": "HOLD", "conviction": "MEDIUM", "rationale": "Tower Bersama Infrastructure stable with recurring tower rental income. 5G rollout provides long-term growth catalyst. Fairly valued.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-23T10:00:00+00:00", "entry_price": 1850, "exit_target": 2100, "stop_loss": 1650, "position_size_pct": 1.2, "risks": ["Tower rental rate pressure", "5G deployment delays", "Interest rate impact on debt"], "analyst_agreement": 3}',
 NOW() - INTERVAL '1 day', NOW(), 'decision:idx-towr-hold-009', 'InvestmentDecision', 'idx-towr-hold-009', 1),
('idx00500000000000000000000001', (SELECT COALESCE(MAX(sequence_id),0)+1 FROM event_journal),
 'decision:idx-klbf-buy-010', 1, 'InvestmentDecisionCreatedEvent',
 '{"decision_id": "urn:karsa:decision:idx:klbf-buy-010", "ticker": "KLBF.JK", "action": "BUY", "conviction": "STRONG", "rationale": "Kalbe Farma is the largest pharmaceutical company in Indonesia. Strong OTC and prescription drug portfolio. Growing healthcare spending in Indonesia.", "proposed_by": "ai-researcher", "proposed_at": "2026-06-22T09:00:00+00:00", "entry_price": 2450, "exit_target": 2900, "stop_loss": 2200, "position_size_pct": 2.0, "risks": ["Generic drug pricing pressure", "Regulatory changes in pharma", "Competition from generic manufacturers"], "analyst_agreement": 4}',
 NOW() - INTERVAL '2 days', NOW(), 'decision:idx-klbf-buy-010', 'InvestmentDecision', 'idx-klbf-buy-010', 1)
ON CONFLICT (event_id) DO NOTHING;

-- Seed additional thesis snapshots
INSERT INTO thesis_snapshots (
    thesis_urn, title, summary, rationale, confidence,
    author_urn, regime_urn, lifecycle_state, snapshot_version,
    assumptions_jsonb, created_at
) VALUES
('urn:karsa:thesis:signal:antm-006', 'ANTM: Nickel EV Play', 'Aneka Tambang benefits from rising nickel demand for EV batteries. Gold mining provides hedge.', 'Nickel demand from EV battery manufacturers increasing. Government divestment adds catalyst.', 6.0, 'ai-researcher', 'regime:stable-growth', 'ACTIVE', 1, '["Nickel demand stays above 5% growth", "EV adoption accelerates in SE Asia"]'::jsonb, NOW() - INTERVAL '3 days'),
('urn:karsa:thesis:signal:goto-007', 'GOTO: Path to Profitability', 'GoTo showing improving unit economics. E-commerce and fintech segments growing.', 'Ride-hailing market leader. Fintech GoPay reaching critical mass. Cost optimization ongoing.', 5.0, 'ai-researcher', 'regime:stable-growth', 'PROPOSED', 1, '["Path to profitability by 2026", "Fintech revenue grows 30% YoY"]'::jsonb, NOW() - INTERVAL '4 days'),
('urn:karsa:thesis:signal:adro-008', 'ADRO: Coal Headwinds', 'Adaro Energy faces coal price headwinds and ESG pressure.', 'Coal prices declining. ESG divestment pressure from institutional investors.', 4.0, 'ai-researcher', 'regime:late-cycle', 'ACTIVE', 1, '["Coal prices stay below $100/ton", "ESG pressure intensifies"]'::jsonb, NOW() - INTERVAL '2 days'),
('urn:karsa:thesis:signal:towr-009', 'TOWR: 5G Tower Play', 'Tower Bersama stable with recurring income. 5G rollout provides growth.', 'Tower rental income stable. 5G deployment creates new tower demand.', 6.0, 'ai-researcher', 'regime:stable-growth', 'ACTIVE', 1, '["5G deployment stays on track", "Tower rental rates stable"]'::jsonb, NOW() - INTERVAL '5 days'),
('urn:karsa:thesis:signal:klbf-010', 'KLBF: Healthcare Growth', 'Kalbe Farma largest pharma in Indonesia. Growing healthcare spending.', 'OTC and prescription drugs growing. Healthcare spending increasing 10% YoY.', 8.0, 'ai-researcher', 'regime:stable-growth', 'ACTIVE', 1, '["Healthcare spending grows above 8%", "OTC market share stays above 20%"]'::jsonb, NOW() - INTERVAL '6 days')
ON CONFLICT DO NOTHING;
