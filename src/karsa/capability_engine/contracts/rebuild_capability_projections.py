"""RebuildCapabilityProjectionsCommand -- Sprint-11. Wave-8.

Command contract for triggering projection rebuilds.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RebuildCapabilityProjectionsCommand:
    """Command to trigger projection rebuilds.

    ADR-135: Checkpoint validation supported.
    """

    projection_name: Optional[str] = None  # None = rebuild all
    source_checkpoint: Optional[int] = None
    current_checkpoint: Optional[int] = None
