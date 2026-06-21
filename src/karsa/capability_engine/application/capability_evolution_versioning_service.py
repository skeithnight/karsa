"""CapabilityEvolutionVersioningService -- Sprint-11. ADR-133.

Canonical governance for evolution records via the version registry.

Implements:
- get_canonical(): retrieve current canonical evolution
- supersede_previous(): mark previous canonical as SUPERSEDED
- promote_canonical(): promote an evolution to CANONICAL status
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from karsa.capability_engine.domain.events.capability_events import (
    CapabilityEvolutionCanonicalChangedEvent,
)
from karsa.capability_engine.domain.exceptions import InvalidEvolutionError
from karsa.capability_engine.domain.value_objects.enums import EvolutionStatus, EvolutionTriggerType
from karsa.capability_engine.application.ports.capability_evolution_port import (
    CapabilityEvolutionPort,
)
from karsa.capability_engine.application.ports.capability_outbox_port import (
    CapabilityOutboxPort,
    OutboxEvent,
)
from karsa.capability_engine.application.ports.capability_version_registry_port import (
    CapabilityVersionRegistryPort,
    VersionRegistryEntry,
)


class CapabilityEvolutionVersioningService:
    """Canonical governance for evolution records.

    ADR-133: Exactly one CANONICAL per (family, evaluation, trigger).
    The evolution aggregate is immutable; this service manages which
    record is the current canonical via the version registry.
    """

    def __init__(
        self,
        evolution_repo: CapabilityEvolutionPort,
        version_registry: CapabilityVersionRegistryPort,
        outbox_repo: CapabilityOutboxPort,
    ) -> None:
        self._evolution_repo = evolution_repo
        self._version_registry = version_registry
        self._outbox_repo = outbox_repo

    def get_canonical(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[VersionRegistryEntry]:
        """Retrieve the current CANONICAL entry for a business identity.

        ADR-133: Returns None if no canonical exists for this identity.
        """
        return self._version_registry.get_canonical(
            capability_family_id, evaluation_id, trigger_type
        )

    def supersede_previous(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
        new_evolution_id: str,
        changed_by: str = "system",
    ) -> Optional[CapabilityEvolutionCanonicalChangedEvent]:
        """Mark the previous CANONICAL as SUPERSEDED and promote new.

        ADR-133: Exactly one CANONICAL at a time. Previous is marked
        SUPERSEDED with a pointer to the new canonical.

        Returns the canonical changed event, or None if no previous existed.
        """
        # Verify the new evolution exists
        new_evolution = self._evolution_repo.get_by_id(new_evolution_id)
        if new_evolution is None:
            raise InvalidEvolutionError(
                f"Evolution {new_evolution_id} not found"
            )

        # Get current canonical before superseding
        current = self._version_registry.get_canonical(
            capability_family_id, evaluation_id, trigger_type
        )
        previous_evolution_id = current.evolution_id if current else None

        # Supersede previous (if exists) and insert new canonical
        self._version_registry.supersede_previous(
            capability_family_id,
            evaluation_id,
            trigger_type,
            new_evolution_id,
        )

        # Insert new canonical entry
        entry = VersionRegistryEntry(
            version_id=str(uuid.uuid4()),
            capability_family_id=capability_family_id,
            evaluation_id=evaluation_id,
            trigger_type=trigger_type,
            evolution_id=new_evolution_id,
            evolution_status=EvolutionStatus.CANONICAL.value,
        )
        self._version_registry.save(entry)

        # Publish event
        event = CapabilityEvolutionCanonicalChangedEvent(
            event_id=str(uuid.uuid4()),
            capability_family_id=capability_family_id,
            evaluation_id=evaluation_id,
            trigger_type=trigger_type,
            previous_evolution_id=previous_evolution_id,
            new_evolution_id=new_evolution_id,
            changed_at=datetime.utcnow().isoformat(),
            changed_by=changed_by,
        )

        outbox_event = OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=json.dumps(event.to_dict()),
            aggregate_id=capability_family_id,
        )
        self._outbox_repo.save_event(outbox_event)

        return event

    def promote_canonical(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
        evolution_id: str,
        changed_by: str = "system",
    ) -> CapabilityEvolutionCanonicalChangedEvent:
        """Promote an evolution to CANONICAL status.

        ADR-133: If a canonical already exists, it is superseded.
        The trigger_type must be a valid EvolutionTriggerType value.

        This is the primary entry point for canonical governance.
        """
        # Validate trigger type
        valid_triggers = {t.value for t in [
            EvolutionTriggerType.REVIEW_FINDING,
            EvolutionTriggerType.ATTRIBUTION_INSIGHT,
            EvolutionTriggerType.EXECUTION_OUTCOME,
            EvolutionTriggerType.GOVERNANCE_ACTION,
        ]}
        if trigger_type not in valid_triggers:
            raise InvalidEvolutionError(
                f"Invalid trigger_type: {trigger_type}. "
                f"Must be one of {valid_triggers}"
            )

        # Verify evolution exists
        evolution = self._evolution_repo.get_by_id(evolution_id)
        if evolution is None:
            raise InvalidEvolutionError(
                f"Evolution {evolution_id} not found"
            )

        # Get current canonical
        current = self._version_registry.get_canonical(
            capability_family_id, evaluation_id, trigger_type
        )
        previous_evolution_id = current.evolution_id if current else None

        if current:
            # Supersede existing canonical
            self._version_registry.supersede_previous(
                capability_family_id,
                evaluation_id,
                trigger_type,
                evolution_id,
            )

        # Insert new canonical
        entry = VersionRegistryEntry(
            version_id=str(uuid.uuid4()),
            capability_family_id=capability_family_id,
            evaluation_id=evaluation_id,
            trigger_type=trigger_type,
            evolution_id=evolution_id,
            evolution_status=EvolutionStatus.CANONICAL.value,
        )
        self._version_registry.save(entry)

        # Publish event
        event = CapabilityEvolutionCanonicalChangedEvent(
            event_id=str(uuid.uuid4()),
            capability_family_id=capability_family_id,
            evaluation_id=evaluation_id,
            trigger_type=trigger_type,
            previous_evolution_id=previous_evolution_id,
            new_evolution_id=evolution_id,
            changed_at=datetime.utcnow().isoformat(),
            changed_by=changed_by,
        )

        outbox_event = OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=json.dumps(event.to_dict()),
            aggregate_id=capability_family_id,
        )
        self._outbox_repo.save_event(outbox_event)

        return event
