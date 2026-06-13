import json
from typing import Optional
from psycopg_pool import ConnectionPool

from karsa.portfolio.domain.repository.portfolio_repository import PortfolioRepository, PortfolioTargetSnapshotRepository
from karsa.portfolio.domain.model.portfolio import Portfolio, PortfolioTargetSnapshot
from karsa.portfolio.infrastructure.storage.portfolio_mapper import PortfolioMapper, PortfolioTargetSnapshotMapper
from karsa.portfolio.infrastructure.storage.portfolio_records import (
    PortfolioRecord, PositionRecord, ExposureMetricsRecord,
    PortfolioTargetSnapshotRecord, TargetPositionRecord
)

class PostgresPortfolioRepository(PortfolioRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _setup_schema(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio (
                        portfolio_id VARCHAR(255) PRIMARY KEY,
                        state VARCHAR(50) NOT NULL,
                        current_target_snapshot_id VARCHAR(255),
                        positions JSONB NOT NULL,
                        exposure_metrics JSONB NOT NULL
                    );
                """)
            conn.commit()

    def save(self, portfolio: Portfolio) -> None:
        record = PortfolioMapper.to_record(portfolio)
        
        positions_json = json.dumps([{
            "position_id": p.position_id,
            "symbol": p.symbol,
            "quantity": p.quantity,
            "average_cost": p.average_cost,
            "market_value": p.market_value
        } for p in record.positions])
        
        exposure_json = json.dumps({
            "gross_exposure": record.exposure_metrics.gross_exposure,
            "net_exposure": record.exposure_metrics.net_exposure,
            "concentration_exposure": record.exposure_metrics.concentration_exposure,
            "cash_ratio": record.exposure_metrics.cash_ratio,
            "leverage_ratio": record.exposure_metrics.leverage_ratio
        })
        
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO portfolio (
                        portfolio_id, state, current_target_snapshot_id, positions, exposure_metrics
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (portfolio_id) DO UPDATE SET
                        state = EXCLUDED.state,
                        current_target_snapshot_id = EXCLUDED.current_target_snapshot_id,
                        positions = EXCLUDED.positions,
                        exposure_metrics = EXCLUDED.exposure_metrics;
                """, (
                    record.portfolio_id,
                    record.state,
                    record.current_target_snapshot_id,
                    positions_json,
                    exposure_json
                ))
            conn.commit()

    def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT portfolio_id, state, current_target_snapshot_id, positions, exposure_metrics FROM portfolio WHERE portfolio_id = %s", (portfolio_id,))
                row = cur.fetchone()
                
        if not row:
            return None
            
        p_data = row[3]
        e_data = row[4]
        
        positions = [
            PositionRecord(
                position_id=p["position_id"],
                symbol=p["symbol"],
                quantity=p["quantity"],
                average_cost=p["average_cost"],
                market_value=p["market_value"]
            ) for p in p_data
        ]
        
        exposure = ExposureMetricsRecord(
            gross_exposure=e_data["gross_exposure"],
            net_exposure=e_data["net_exposure"],
            concentration_exposure=e_data["concentration_exposure"],
            cash_ratio=e_data["cash_ratio"],
            leverage_ratio=e_data["leverage_ratio"]
        )
        
        record = PortfolioRecord(
            portfolio_id=row[0],
            state=row[1],
            current_target_snapshot_id=row[2],
            positions=positions,
            exposure_metrics=exposure
        )
        
        return PortfolioMapper.to_domain(record)

    def exists(self, portfolio_id: str) -> bool:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM portfolio WHERE portfolio_id = %s", (portfolio_id,))
                return cur.fetchone() is not None

    def delete(self, portfolio_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM portfolio WHERE portfolio_id = %s", (portfolio_id,))
            conn.commit()

class PostgresTargetSnapshotRepository(PortfolioTargetSnapshotRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _setup_schema(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_target_snapshot (
                        snapshot_id VARCHAR(255) PRIMARY KEY,
                        portfolio_id VARCHAR(255) NOT NULL,
                        version INT NOT NULL,
                        target_positions JSONB NOT NULL,
                        created_at VARCHAR(100) NOT NULL
                    );
                """)
            conn.commit()

    def save(self, snapshot: PortfolioTargetSnapshot) -> None:
        record = PortfolioTargetSnapshotMapper.to_record(snapshot)
        
        targets_json = json.dumps([{
            "symbol": t.symbol,
            "target_weight": t.target_weight
        } for t in record.target_positions])
        
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO portfolio_target_snapshot (
                        snapshot_id, portfolio_id, version, target_positions, created_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_id) DO UPDATE SET
                        target_positions = EXCLUDED.target_positions;
                """, (
                    record.snapshot_id,
                    record.portfolio_id,
                    record.version,
                    targets_json,
                    record.created_at
                ))
            conn.commit()

    def get_by_id(self, snapshot_id: str) -> Optional[PortfolioTargetSnapshot]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT snapshot_id, portfolio_id, version, target_positions, created_at FROM portfolio_target_snapshot WHERE snapshot_id = %s", (snapshot_id,))
                row = cur.fetchone()
                
        if not row:
            return None
            
        t_data = row[3]
        
        targets = [
            TargetPositionRecord(
                symbol=t["symbol"],
                target_weight=t["target_weight"]
            ) for t in t_data
        ]
        
        record = PortfolioTargetSnapshotRecord(
            snapshot_id=row[0],
            portfolio_id=row[1],
            version=row[2],
            target_positions=targets,
            created_at=row[4]
        )
        
        return PortfolioTargetSnapshotMapper.to_domain(record)

    def exists(self, snapshot_id: str) -> bool:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM portfolio_target_snapshot WHERE snapshot_id = %s", (snapshot_id,))
                return cur.fetchone() is not None

    def delete(self, snapshot_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM portfolio_target_snapshot WHERE snapshot_id = %s", (snapshot_id,))
            conn.commit()
