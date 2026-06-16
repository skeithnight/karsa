from psycopg_pool import ConnectionPool
from typing import List, Optional
from datetime import datetime
from karsa.portfolio.repositories import ValuationRepository, PositionRepository, CashLedgerRepository
from karsa.portfolio.models import ValuationAggregate, PositionAggregate, CashLedgerAggregate

class PostgresValuationRepository(ValuationRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def find_latest_by_portfolio(self, portfolio_id: str) -> Optional[ValuationAggregate]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT net_asset_value, cash_balance FROM portfolio_read_valuations WHERE portfolio_id = %s",
                    (portfolio_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return ValuationAggregate(
                    portfolio_id=portfolio_id,
                    net_asset_value=row[0],
                    cash_balance=row[1]
                )

    def save(self, valuation: ValuationAggregate) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_read_valuations (portfolio_id, net_asset_value, cash_balance, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        net_asset_value = EXCLUDED.net_asset_value,
                        cash_balance = EXCLUDED.cash_balance,
                        updated_at = NOW()
                    """,
                    (valuation.portfolio_id, valuation.net_asset_value, valuation.cash_balance)
                )

    def list_all_by_portfolio(self, portfolio_id: str) -> List[ValuationAggregate]:
        latest = self.find_latest_by_portfolio(portfolio_id)
        return [latest] if latest else []

class PostgresPositionRepository(PositionRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def find_all_by_portfolio(self, portfolio_id: str) -> List[PositionAggregate]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT asset_id, quantity, average_cost, market_value, exposure_pct, exposure_value
                    FROM portfolio_read_positions
                    WHERE portfolio_id = %s
                    """,
                    (portfolio_id,)
                )
                rows = cur.fetchall()
                return [
                    PositionAggregate(
                        portfolio_id=portfolio_id,
                        asset_id=row[0],
                        quantity=row[1],
                        average_cost=row[2],
                        market_value=row[3],
                        exposure_pct=row[4],
                        exposure_value=row[5]
                    ) for row in rows
                ]

    def find_by_portfolio_and_asset(self, portfolio_id: str, asset_id: str) -> Optional[PositionAggregate]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT quantity, average_cost, market_value, exposure_pct, exposure_value
                    FROM portfolio_read_positions
                    WHERE portfolio_id = %s AND asset_id = %s
                    """,
                    (portfolio_id, asset_id)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return PositionAggregate(
                    portfolio_id=portfolio_id,
                    asset_id=asset_id,
                    quantity=row[0],
                    average_cost=row[1],
                    market_value=row[2],
                    exposure_pct=row[3],
                    exposure_value=row[4]
                )

    def save(self, position: PositionAggregate) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_read_positions (asset_id, portfolio_id, quantity, average_cost, market_value, exposure_pct, exposure_value, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (asset_id) DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        average_cost = EXCLUDED.average_cost,
                        market_value = EXCLUDED.market_value,
                        exposure_pct = EXCLUDED.exposure_pct,
                        exposure_value = EXCLUDED.exposure_value,
                        updated_at = NOW()
                    """,
                    (position.asset_id, position.portfolio_id, position.quantity, position.average_cost, position.market_value, position.exposure_pct, position.exposure_value)
                )

    def list_active_by_portfolio(self, portfolio_id: str) -> List[PositionAggregate]:
        return self.find_all_by_portfolio(portfolio_id)

class PostgresCashLedgerRepository(CashLedgerRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def find_by_portfolio(self, portfolio_id: str) -> Optional[CashLedgerAggregate]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT balance FROM portfolio_read_cash_ledgers WHERE portfolio_id = %s",
                    (portfolio_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return CashLedgerAggregate(
                    portfolio_id=portfolio_id,
                    balance=row[0]
                )

    def save(self, ledger: CashLedgerAggregate) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO portfolio_read_cash_ledgers (portfolio_id, balance, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        balance = EXCLUDED.balance,
                        updated_at = NOW()
                    """,
                    (ledger.portfolio_id, ledger.balance)
                )

