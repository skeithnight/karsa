"""Repository for dead-letter persistence.

Writes normalization failures to data_bridge_dead_letter table.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from karsa.providers.domain.normalization import DeadLetterEntry


class DeadLetterRepository:
    """Append-only writes to data_bridge_dead_letter."""

    def __init__(self, session: Session):
        self.session = session

    def append(self, entry: DeadLetterEntry) -> None:
        """Write a normalization failure to the dead-letter table."""
        from sqlalchemy import text
        self.session.execute(
            text("""
                INSERT INTO data_bridge_dead_letter
                    (provider_id, raw_payload, error_message, error_type, received_at)
                VALUES
                    (:provider_id, :raw_payload, :error_message, :error_type, :received_at)
            """),
            {
                "provider_id": entry.provider_id,
                "raw_payload": json.dumps(entry.raw_payload),
                "error_message": entry.error_message,
                "error_type": entry.error_type,
                "received_at": entry.received_at or datetime.now(timezone.utc),
            },
        )
