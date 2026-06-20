from sqlalchemy import text
from karsa.attribution.domain.events import (
    AttributionCalculatedEvent, CreditAllocatedEvent
)

class AttributionProjectionService:
    def get_events(self):
        return [
            "AttributionCalculatedEvent",
            "CreditAllocatedEvent"
        ]

    def handle(self, event, conn):
        event_type = event["event_type"]
        seq = event["stream_version"]
        payload = event["payload"]
        
        if event_type == "AttributionCalculatedEvent":
            conn.execute(text("""
                INSERT INTO attribution_snapshots (attribution_urn, review_urn, benchmark_urn, absolute_return, benchmark_return, true_alpha, stream_version)
                VALUES (:urn, :rurn, :burn, :absr, :br, :talpha, :seq)
                ON CONFLICT (attribution_urn) DO UPDATE SET
                    review_urn = EXCLUDED.review_urn,
                    benchmark_urn = EXCLUDED.benchmark_urn,
                    absolute_return = EXCLUDED.absolute_return,
                    benchmark_return = EXCLUDED.benchmark_return,
                    true_alpha = EXCLUDED.true_alpha,
                    stream_version = EXCLUDED.stream_version
            """), {
                "urn": payload["attribution_urn"], "rurn": payload["review_urn"],
                "burn": payload["benchmark_urn"], "absr": payload["absolute_return"],
                "br": payload["benchmark_return"], "talpha": payload["true_alpha"], "seq": seq
            })
            
        elif event_type == "CreditAllocatedEvent":
            conn.execute(text("""
                INSERT INTO attribution_nodes (node_id, attribution_urn, parent_node_id, subject_type, subject_urn, skill_ratio, luck_ratio, stream_version)
                VALUES (:nid, :urn, :pnid, :stype, :surn, :sratio, :lratio, :seq)
                ON CONFLICT (node_id) DO UPDATE SET
                    stream_version = EXCLUDED.stream_version
            """), {
                "nid": payload["node_id"], "urn": payload["attribution_urn"], "pnid": payload["parent_node_id"],
                "stype": payload["subject_type"], "surn": payload["subject_urn"],
                "sratio": payload["skill_ratio"], "lratio": payload["luck_ratio"], "seq": seq
            })
