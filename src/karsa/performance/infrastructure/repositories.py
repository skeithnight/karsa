from typing import Optional, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..domain.projections import DecisionContext, DecisionPerformanceRecord
from ..domain.value_objects import DecisionPerformanceIdentity

class DecisionContextMissingError(Exception):
    pass

class PerformanceProjectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_context(self, context: DecisionContext) -> None:
        stmt = text("""
            INSERT INTO projection_decision_context 
            (decision_id, worker_id, strategy_id, thesis_id, stated_confidence, decision_timestamp)
            VALUES (:decision_id, :worker_id, :strategy_id, :thesis_id, :stated_confidence, :decision_timestamp)
            ON CONFLICT (decision_id) DO UPDATE SET
            worker_id = EXCLUDED.worker_id,
            strategy_id = EXCLUDED.strategy_id,
            thesis_id = EXCLUDED.thesis_id,
            stated_confidence = EXCLUDED.stated_confidence,
            decision_timestamp = EXCLUDED.decision_timestamp
        """)
        self.session.execute(stmt, {
            "decision_id": context.decision_id,
            "worker_id": context.worker_id,
            "strategy_id": context.strategy_id,
            "thesis_id": context.thesis_id,
            "stated_confidence": context.stated_confidence,
            "decision_timestamp": context.decision_timestamp
        })

    def get_context(self, decision_id: str) -> DecisionContext:
        stmt = text("SELECT * FROM projection_decision_context WHERE decision_id = :decision_id")
        result = self.session.execute(stmt, {"decision_id": decision_id}).fetchone()
        if not result:
            raise DecisionContextMissingError(f"Context missing for {decision_id}")
        
        return DecisionContext(
            decision_id=result.decision_id,
            worker_id=result.worker_id,
            strategy_id=result.strategy_id,
            thesis_id=result.thesis_id,
            stated_confidence=result.stated_confidence,
            decision_timestamp=result.decision_timestamp
        )

    def append_decision_record(self, record: DecisionPerformanceRecord) -> None:
        stmt = text("""
            INSERT INTO projection_decision_performance
            (decision_id, outcome_sequence_id, attribution_generation, worker_id, strategy_id, thesis_id, regime_id, gross_pnl, net_pnl, stated_confidence, decision_timestamp, projection_schema_version, calculation_version)
            VALUES
            (:decision_id, :outcome_sequence_id, :attribution_generation, :worker_id, :strategy_id, :thesis_id, :regime_id, :gross_pnl, :net_pnl, :stated_confidence, :decision_timestamp, :projection_schema_version, :calculation_version)
            ON CONFLICT (decision_id, outcome_sequence_id, attribution_generation) DO NOTHING
        """)
        self.session.execute(stmt, {
            "decision_id": record.identity.decision_id,
            "outcome_sequence_id": record.identity.outcome_sequence_id,
            "attribution_generation": record.identity.attribution_generation,
            "worker_id": record.worker_id,
            "strategy_id": record.strategy_id,
            "thesis_id": record.thesis_id,
            "regime_id": record.regime_id,
            "gross_pnl": record.gross_pnl,
            "net_pnl": record.net_pnl,
            "stated_confidence": record.stated_confidence,
            "decision_timestamp": record.decision_timestamp,
            "projection_schema_version": record.projection_schema_version,
            "calculation_version": record.calculation_version
        })

    def get_effective_generation_record(self, decision_id: str, outcome_sequence_id: int) -> Optional[DecisionPerformanceRecord]:
        stmt = text("""
            SELECT * 
            FROM projection_decision_performance
            WHERE decision_id = :decision_id AND outcome_sequence_id = :outcome_sequence_id
            ORDER BY attribution_generation DESC LIMIT 1
        """)
        result = self.session.execute(stmt, {
            "decision_id": decision_id,
            "outcome_sequence_id": outcome_sequence_id
        }).fetchone()
        
        if result:
            return DecisionPerformanceRecord(
                identity=DecisionPerformanceIdentity(
                    decision_id=result.decision_id,
                    outcome_sequence_id=result.outcome_sequence_id,
                    attribution_generation=result.attribution_generation
                ),
                worker_id=result.worker_id,
                strategy_id=result.strategy_id,
                thesis_id=result.thesis_id,
                regime_id=result.regime_id,
                gross_pnl=result.gross_pnl,
                net_pnl=result.net_pnl,
                stated_confidence=result.stated_confidence,
                decision_timestamp=result.decision_timestamp,
                projection_schema_version=result.projection_schema_version,
                calculation_version=result.calculation_version
            )
        return None

    def apply_bucket_delta(self, target_type: str, target_id: str, bucket_date: date, delta_gross: Decimal, delta_net: Decimal) -> None:
        stmt = text("""
            INSERT INTO projection_daily_pnl_bucket (target_type, target_id, bucket_date, daily_gross_pnl, daily_net_pnl)
            VALUES (:target_type, :target_id, :bucket_date, :delta_gross, :delta_net)
            ON CONFLICT (target_type, target_id, bucket_date)
            DO UPDATE SET 
                daily_gross_pnl = projection_daily_pnl_bucket.daily_gross_pnl + EXCLUDED.daily_gross_pnl,
                daily_net_pnl = projection_daily_pnl_bucket.daily_net_pnl + EXCLUDED.daily_net_pnl
        """)
        self.session.execute(stmt, {
            "target_type": target_type,
            "target_id": target_id,
            "bucket_date": bucket_date,
            "delta_gross": delta_gross,
            "delta_net": delta_net
        })

