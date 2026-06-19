from karsa.shared.domain.event import DomainEvent

class ReviewInitiatedEvent(DomainEvent):
    def __init__(self, review_urn: str, target_type: str, target_urn: str):
        super().__init__()
        self.payload = {
            "review_urn": review_urn,
            "target_type": target_type,
            "target_urn": target_urn
        }

class EvidenceAttachedEvent(DomainEvent):
    def __init__(self, review_urn: str, source_type: str, source_urn: str, snapshot_version: int, fingerprint_sha256: str):
        super().__init__()
        self.payload = {
            "review_urn": review_urn,
            "source_type": source_type,
            "source_urn": source_urn,
            "snapshot_version": snapshot_version,
            "fingerprint_sha256": fingerprint_sha256
        }

class CalibrationGradedEvent(DomainEvent):
    def __init__(self, review_urn: str, calibration_score: float, rationale: str):
        super().__init__()
        self.payload = {
            "review_urn": review_urn,
            "calibration_score": calibration_score,
            "rationale": rationale
        }

class ReviewSealedEvent(DomainEvent):
    def __init__(self, review_urn: str, target_type: str, target_urn: str, accuracy: float, parent_review_urn: str, supersedes_review_urn: str, lineage_type: str):
        super().__init__()
        self.payload = {
            "review_urn": review_urn,
            "target_type": target_type,
            "target_urn": target_urn,
            "accuracy": accuracy,
            "parent_review_urn": parent_review_urn,
            "supersedes_review_urn": supersedes_review_urn,
            "lineage_type": lineage_type
        }
