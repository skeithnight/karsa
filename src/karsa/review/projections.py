from sqlalchemy import text
from karsa.review.domain.events import (
    ReviewInitiatedEvent, EvidenceAttachedEvent, CalibrationGradedEvent, ReviewSealedEvent
)

class ReviewProjectionService:
    def get_events(self):
        return [
            "ReviewInitiatedEvent",
            "EvidenceAttachedEvent",
            "CalibrationGradedEvent",
            "ReviewSealedEvent"
        ]

    def handle(self, event, conn):
        event_type = event["event_type"]
        seq = event["stream_version"]
        payload = event["payload"]
        
        if event_type == "ReviewInitiatedEvent":
            conn.execute(text("""
                INSERT INTO review_snapshots (review_urn, target_type, target_urn, state, stream_version)
                VALUES (:urn, :ttype, :turn, 'PENDING', :seq)
                ON CONFLICT (review_urn) DO UPDATE SET 
                    target_type = EXCLUDED.target_type,
                    target_urn = EXCLUDED.target_urn,
                    state = EXCLUDED.state,
                    stream_version = EXCLUDED.stream_version
            """), {"urn": payload["review_urn"], "ttype": payload["target_type"], "turn": payload["target_urn"], "seq": seq})
            
        elif event_type == "CalibrationGradedEvent":
            conn.execute(text("""
                INSERT INTO calibration_snapshots (review_urn, stated_confidence, actual_accuracy, calibration_delta, stream_version)
                VALUES (:urn, 0, 0, :score, :seq)
                ON CONFLICT (review_urn) DO UPDATE SET
                    calibration_delta = EXCLUDED.calibration_delta,
                    stream_version = EXCLUDED.stream_version
            """), {"urn": payload["review_urn"], "score": payload["calibration_score"], "seq": seq})
            
        elif event_type == "ReviewSealedEvent":
            conn.execute(text("""
                UPDATE review_snapshots SET state = 'SEALED', accuracy = :acc, lineage_type = :ltype, stream_version = :seq
                WHERE review_urn = :urn
            """), {"urn": payload["review_urn"], "acc": payload["accuracy"], "ltype": payload["lineage_type"], "seq": seq})
