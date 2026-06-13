import psycopg
from psycopg_pool import ConnectionPool
from typing import Optional
import json
from karsa.thesis.domain.repository.thesis_repository import ThesisRepository
from karsa.thesis.domain.model.thesis import ActiveThesis
from karsa.thesis.infrastructure.storage.thesis_mapper import ThesisMapper
from karsa.thesis.infrastructure.storage.thesis_records import ThesisRecord

class PostgresThesisRepository(ThesisRepository):
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def _setup_schema(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS thesis_active (
                        thesis_id VARCHAR(255) PRIMARY KEY,
                        author VARCHAR(255) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        state VARCHAR(50) NOT NULL,
                        versions JSONB NOT NULL DEFAULT '[]',
                        reviews JSONB NOT NULL DEFAULT '[]',
                        invalidation_rules JSONB NOT NULL DEFAULT '[]',
                        dependency_graph JSONB
                    );
                """)
            conn.commit()

    def save(self, thesis: ActiveThesis) -> None:
        record = ThesisMapper.to_record(thesis)
        
        versions_json = json.dumps([v.__dict__ for v in record.versions], default=str)
        reviews_json = json.dumps([r.__dict__ for r in record.reviews], default=str)
        rules_json = json.dumps([r.__dict__ for r in record.invalidation_rules])
        graph_json = json.dumps(record.dependency_graph.__dict__) if record.dependency_graph else None
        
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO thesis_active (
                        thesis_id, author, created_at, state, 
                        versions, reviews, invalidation_rules, dependency_graph
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (thesis_id) DO UPDATE SET
                        state = EXCLUDED.state,
                        versions = EXCLUDED.versions,
                        reviews = EXCLUDED.reviews,
                        invalidation_rules = EXCLUDED.invalidation_rules,
                        dependency_graph = EXCLUDED.dependency_graph;
                """, (
                    record.thesis_id,
                    record.author,
                    record.created_at,
                    record.state,
                    versions_json,
                    reviews_json,
                    rules_json,
                    graph_json
                ))
            conn.commit()

    def get_by_id(self, thesis_id: str) -> Optional[ActiveThesis]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM thesis_active WHERE thesis_id = %s", (thesis_id,))
                row = cur.fetchone()
                
        if not row:
            return None
            
        from karsa.thesis.infrastructure.storage.thesis_records import (
            ThesisVersionRecord, ThesisReviewRecord, ThesisInvalidationRuleRecord, 
            ThesisDependencyGraphRecord, ThesisDependencyEdgeRecord
        )
        from datetime import datetime

        # row indices: 0:id, 1:author, 2:created_at, 3:state, 4:versions, 5:reviews, 6:rules, 7:graph
        versions = []
        for v in row[4]:
            created_at = datetime.fromisoformat(v["created_at"]) if isinstance(v["created_at"], str) else v["created_at"]
            versions.append(ThesisVersionRecord(v["version_id"], v["derived_from"], created_at, v["content_hash"]))
            
        reviews = []
        for r in row[5]:
            reviewed_at = datetime.fromisoformat(r["reviewed_at"]) if isinstance(r["reviewed_at"], str) else r["reviewed_at"]
            reviews.append(ThesisReviewRecord(r["review_id"], r["reviewer"], reviewed_at, r["outcome"], r["notes"]))
            
        rules = []
        for ru in row[6]:
            rules.append(ThesisInvalidationRuleRecord(ru["rule_id"], ru["metric_name"], float(ru["threshold"]), ru["comparator"], bool(ru["is_breached"])))
            
        graph = None
        if row[7]:
            g_data = row[7]
            edges = []
            for e in g_data.get("edges", []):
                edges.append(ThesisDependencyEdgeRecord(e["dependency_thesis_id"], float(e["impact_weight"]), e["description"]))
            graph = ThesisDependencyGraphRecord(g_data["graph_id"], edges)
            
        record = ThesisRecord(
            thesis_id=row[0],
            author=row[1],
            created_at=row[2],
            state=row[3],
            versions=versions,
            reviews=reviews,
            invalidation_rules=rules,
            dependency_graph=graph
        )
        
        return ThesisMapper.to_domain(record)

    def exists(self, thesis_id: str) -> bool:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM thesis_active WHERE thesis_id = %s", (thesis_id,))
                return cur.fetchone() is not None

    def delete(self, thesis_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM thesis_active WHERE thesis_id = %s", (thesis_id,))
            conn.commit()
