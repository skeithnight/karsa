from typing import Optional
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class URN:
    """Represents a standardized Karsa URN."""
    domain: str
    asset: str
    category: Optional[str] = None
    timestamp_or_version: Optional[str] = None
    hash_val: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [self.domain]
        if self.domain == "evidence" and self.category:
            parts.extend(["idx", self.category, self.timestamp_or_version or "", self.hash_val or ""])
        elif self.domain in ("research", "thesis", "forecast", "decision"):
            parts.append(self.asset)
            if self.timestamp_or_version:
                parts.append(self.timestamp_or_version)
        return ":".join(parts)

    @classmethod
    def parse(cls, urn_str: str) -> "URN":
        parts = urn_str.split(":")
        if not parts:
            raise ValueError(f"Invalid URN format: {urn_str}")
            
        domain = parts[0]
        if domain == "evidence":
            if len(parts) != 5 or parts[1] != "idx":
                raise ValueError(f"Invalid evidence URN format: {urn_str}")
            return cls(domain=domain, asset="idx", category=parts[2], timestamp_or_version=parts[3], hash_val=parts[4])
        
        if domain in ("research", "thesis", "forecast", "decision"):
            if len(parts) < 2:
                raise ValueError(f"Invalid {domain} URN format: {urn_str}")
            timestamp = parts[-1] if len(parts) > 2 else None
            asset_parts = parts[1:-1] if len(parts) > 2 else parts[1:]
            return cls(domain=domain, asset=":".join(asset_parts), timestamp_or_version=timestamp)
            
        raise ValueError(f"Unknown URN domain: {domain}")
