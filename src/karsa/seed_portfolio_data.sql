-- Sprint-63: Portfolio Data Seed Script
-- Realistic IDX portfolio data for frontend display
-- Run: docker exec -i karsa-postgres-1 psql -U karsa -d karsa_db < src/karsa/seed_portfolio_data.sql

-- Update portfolio positions with market values
UPDATE portfolio_read_positions SET
    market_value = 92750000,
    exposure_pct = 14.87,
    exposure_value = 92750000,
    updated_at = NOW()
WHERE asset_id = 'BBCA.JK';

UPDATE portfolio_read_positions SET
    market_value = 6180000,
    exposure_pct = 0.99,
    exposure_value = 6180000,
    updated_at = NOW()
WHERE asset_id = 'BBRI.JK';

UPDATE portfolio_read_positions SET
    market_value = 5950000,
    exposure_pct = 0.95,
    exposure_value = 5950000,
    updated_at = NOW()
WHERE asset_id = 'BMRI.JK';

UPDATE portfolio_read_positions SET
    market_value = 9820000,
    exposure_pct = 1.57,
    exposure_value = 9820000,
    updated_at = NOW()
WHERE asset_id = 'ASII.JK';

UPDATE portfolio_read_positions SET
    market_value = 9240000,
    exposure_pct = 1.48,
    exposure_value = 9240000,
    updated_at = NOW()
WHERE asset_id = 'TLKM.JK';

-- Update portfolio valuation: NAV = sum of market values + cash
-- Market values: 92.75M + 6.18M + 5.95M + 9.82M + 9.24M = 123.94M
-- Cash: 500M
-- Total NAV: ~624M
UPDATE portfolio_read_valuations SET
    net_asset_value = 624000000,
    cash_balance = 500000000,
    updated_at = NOW()
WHERE portfolio_id = 'PORT-MAIN';

-- Update cash ledger
UPDATE portfolio_read_cash_ledgers SET
    balance = 500000000,
    updated_at = NOW()
WHERE portfolio_id = 'PORT-MAIN';
