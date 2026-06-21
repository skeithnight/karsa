"""CapabilityTimeseriesResponse -- Sprint-12. Wave-3.

Transport response DTO for capability score time series.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TimeseriesEntryResponse(BaseModel):
    """Single entry in the score time series."""

    evaluation_sequence: int
    score: float
    algorithm_version: str
    recorded_at: datetime
    capability_version_id: Optional[str] = None


class CapabilityTimeseriesResponse(BaseModel):
    """Response for GET /capabilities/{family_id}/timeseries."""

    capability_family_id: str
    entries: List[TimeseriesEntryResponse] = []
