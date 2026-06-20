from datetime import datetime
from .urn import URN

class URNBuilder:
    @staticmethod
    def build_evidence_urn(category: str, date: str, payload_hash: str) -> URN:
        return URN(domain="evidence", asset="idx", category=category, timestamp_or_version=date, hash_val=payload_hash)
        
    @staticmethod
    def build_research_urn(asset: str, timestamp: datetime) -> URN:
        return URN(domain="research", asset=asset, timestamp_or_version=str(int(timestamp.timestamp())))

    @staticmethod
    def build_thesis_urn(asset: str, version: int) -> URN:
        return URN(domain="thesis", asset=asset, timestamp_or_version=f"v{version}")

    @staticmethod
    def build_forecast_urn(asset: str, timestamp: datetime) -> URN:
        return URN(domain="forecast", asset=asset, timestamp_or_version=str(int(timestamp.timestamp())))

    @staticmethod
    def build_decision_urn(asset: str, timestamp: datetime) -> URN:
        return URN(domain="decision", asset=asset, timestamp_or_version=str(int(timestamp.timestamp())))
