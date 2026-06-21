"""MemoRevision child entity -- Sprint-15."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class MemoRevision:
    """Child entity tracking memo revision history.

    Stored as JSONB within the parent aggregate.
    """

    revision_number: int
    thesis: str
    conviction_level: str
    revised_by: str
    revision_reason: str = ""
    revised_at: datetime = field(default_factory=datetime.utcnow)
