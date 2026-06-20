from sqlalchemy import text
from typing import List, Optional
from karsa.thesis.intelligence.api.dtos import (
    TimelineEventDto, ConfidencePointDto, AssumptionIntelligenceDto,
    AssumptionTimelineDto, ThesisHealthDto
)

class PostgresThesisIntelligenceRepository:
    def __init__(self, db_engine):
        self.engine = db_engine

    def get_timeline(self, thesis_urn: str) -> List[TimelineEventDto]:
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM thesis_timeline WHERE thesis_urn = :urn ORDER BY stream_version ASC"),
                {"urn": thesis_urn}
            ).fetchall()
            return [TimelineEventDto(**dict(row._mapping)) for row in result]

    def get_confidence_history(self, thesis_urn: str) -> List[ConfidencePointDto]:
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM confidence_history WHERE thesis_urn = :urn ORDER BY stream_version ASC"),
                {"urn": thesis_urn}
            ).fetchall()
            return [ConfidencePointDto(**dict(row._mapping)) for row in result]

    def get_assumptions(self, thesis_urn: str) -> List[AssumptionIntelligenceDto]:
        with self.engine.connect() as conn:
            snapshots = conn.execute(
                text("SELECT * FROM assumption_snapshots WHERE thesis_urn = :urn"),
                {"urn": thesis_urn}
            ).fetchall()
            
            result = []
            for snap in snapshots:
                timeline_rows = conn.execute(
                    text("SELECT * FROM assumption_timeline WHERE assumption_urn = :a_urn ORDER BY timestamp ASC"),
                    {"a_urn": snap.assumption_urn}
                ).fetchall()
                timeline = [AssumptionTimelineDto(**dict(r._mapping)) for r in timeline_rows]
                
                dto = AssumptionIntelligenceDto(
                    assumption_urn=snap.assumption_urn,
                    statement=snap.statement,
                    is_valid=snap.is_valid,
                    challenge_count=snap.challenge_count,
                    timeline=timeline
                )
                result.append(dto)
            return result

    def get_assumption_timeline(self, assumption_urn: str) -> List[AssumptionTimelineDto]:
        with self.engine.connect() as conn:
            timeline_rows = conn.execute(
                text("SELECT * FROM assumption_timeline WHERE assumption_urn = :urn ORDER BY timestamp ASC"),
                {"urn": assumption_urn}
            ).fetchall()
            return [AssumptionTimelineDto(**dict(r._mapping)) for r in timeline_rows]

    def get_health(self, thesis_urn: str) -> Optional[ThesisHealthDto]:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM thesis_health_snapshots WHERE thesis_urn = :urn"),
                {"urn": thesis_urn}
            ).fetchone()
            if not row:
                return None
            return ThesisHealthDto(**dict(row._mapping))
