"""CapabilityScoringService -- Sprint-11. Transaction B.

ADR-132: Separate aggregate, separate transaction from evolution.
ADR-134: Algorithm versioning.
ADR-136: Monotonic evaluation ordering.
ADR-137: Version boundary tracking.
ADR-138: Governance consecutive score counters.

Transaction B ONLY:
1. Load CapabilityHealthScore
2. Load CapabilityScoreHistory
3. Validate evaluation ordering
4. Apply scoring algorithm
5. Persist score history
6. Update CapabilityHealthScore
7. OCC retry support

Must NOT:
- touch CapabilityEvolution records
- touch version registry
- touch outbox
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.events.capability_events import (
    CapabilityHealthScoreUpdatedEvent,
    GovernanceCapabilitySuspendedEvent,
    GovernanceCapabilityUnsuspendedEvent,
    ScoringAlgorithmChangedEvent,
)
from karsa.capability_engine.domain.exceptions import (
    EvaluationOrderingError,
    InvalidHealthScoreError,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.application.ports.capability_health_score_port import (
    CapabilityHealthScorePort,
)
from karsa.capability_engine.application.ports.capability_outbox_port import (
    CapabilityOutboxPort,
    OutboxEvent,
)
from karsa.capability_engine.application.ports.capability_score_history_port import (
    CapabilityScoreHistoryPort,
)


# ADR-138: Governance thresholds
DEFAULT_LOW_THRESHOLD = 0.3
DEFAULT_HIGH_THRESHOLD = 0.7
SUSPEND_THRESHOLD = 3  # consecutive low scores
UNSUSPEND_THRESHOLD = 2  # consecutive high scores
DEFAULT_MAX_OCC_RETRIES = 3


@dataclass
class ScoringCommand:
    """Input DTO for recording a health score evaluation."""

    capability_family_id: str
    evaluation_id: str
    evaluation_sequence: int
    capability_version_id: str  # ADR-137
    score: float  # 0.0-1.0
    components: List[CapabilityScoreComponent]
    algorithm_version: str = "v1.0"  # ADR-134
    capability_urn: str = ""  # for governance events


@dataclass
class ScoringResult:
    """Output DTO from scoring."""

    success: bool
    health_score_id: Optional[str] = None
    previous_score: Optional[float] = None
    new_score: Optional[float] = None
    events: Optional[List] = None
    occ_retries: int = 0


class CapabilityScoringService:
    """Transaction B: Health score evaluation and history persistence.

    ADR-130: Strict transaction boundary -- does NOT touch evolution
    records, version registry, or outbox. Those belong to Transaction A
    (CapabilityEvolutionService).
    """

    def __init__(
        self,
        health_score_repo: CapabilityHealthScorePort,
        score_history_repo: CapabilityScoreHistoryPort,
        outbox_repo: CapabilityOutboxPort,
        max_occ_retries: int = DEFAULT_MAX_OCC_RETRIES,
        low_threshold: float = DEFAULT_LOW_THRESHOLD,
        high_threshold: float = DEFAULT_HIGH_THRESHOLD,
    ) -> None:
        self._health_score_repo = health_score_repo
        self._score_history_repo = score_history_repo
        self._outbox_repo = outbox_repo
        self._max_occ_retries = max_occ_retries
        self._low_threshold = low_threshold
        self._high_threshold = high_threshold

    def record_evaluation(self, command: ScoringCommand) -> ScoringResult:
        """Execute Transaction B: record a score evaluation with OCC retry.

        Steps:
        1. Load CapabilityHealthScore
        2. Load CapabilityScoreHistory (last sequence)
        3. Validate evaluation ordering (ADR-136)
        4. Apply scoring algorithm
        5. Persist score history
        6. Update CapabilityHealthScore (OCC)
        7. Retry on OCC conflict
        """
        for attempt in range(self._max_occ_retries + 1):
            result = self._try_record_evaluation(command, attempt)
            if result.success:
                return result
            # OCC conflict -- retry
        return ScoringResult(
            success=False,
            occ_retries=self._max_occ_retries,
            events=[],
        )

    def _try_record_evaluation(
        self, command: ScoringCommand, attempt: int
    ) -> ScoringResult:
        """Single attempt at recording an evaluation.

        Each attempt reloads the aggregate fresh so that a prior failed
        save (OCC conflict) does not leave stale mutation state.
        """
        # Step 1: Load health score aggregate (fresh each attempt)
        health_score = self._health_score_repo.get_by_family_id(
            command.capability_family_id
        )

        is_new = False
        if health_score is None:
            health_score = CapabilityHealthScore(
                health_score_id=str(uuid.uuid4()),
                capability_family_id=command.capability_family_id,
                algorithm_version=command.algorithm_version,
            )
            is_new = True

        previous_score = health_score.current_score

        # Step 2: Load last recorded sequence from history
        last_sequence = self._score_history_repo.get_last_sequence(
            command.capability_family_id
        )

        # Step 3: Validate evaluation ordering (ADR-136)
        effective_last = max(
            health_score.last_recorded_sequence, last_sequence
        )
        if command.evaluation_sequence <= effective_last:
            raise EvaluationOrderingError(
                f"evaluation_sequence {command.evaluation_sequence} must be > "
                f"last_recorded_sequence {effective_last}"
            )

        # Step 4: Apply scoring algorithm (delegate to aggregate)
        health_score.record_evaluation(
            score=command.score,
            components=command.components,
            evaluation_sequence=command.evaluation_sequence,
            algorithm_version=command.algorithm_version,
            low_threshold=self._low_threshold,
            high_threshold=self._high_threshold,
        )

        # Step 5: Update health score aggregate (OCC) BEFORE history
        # If save fails, no history entry is left behind.
        saved = self._health_score_repo.save(health_score)
        if not saved:
            return ScoringResult(success=False, occ_retries=attempt)

        # Step 6: Persist score history (append-only, only after successful save)
        history_entry = ScoreHistoryEntry(
            capability_family_id=command.capability_family_id,
            evaluation_id=command.evaluation_id,
            evaluation_sequence=command.evaluation_sequence,
            capability_version_id=command.capability_version_id,
            score=command.score,
            algorithm_version=command.algorithm_version,
            components=command.components,
        )
        self._score_history_repo.append(history_entry)

        # Step 7: Build events
        events = self._build_events(
            health_score, previous_score, command, is_new
        )

        # Publish to outbox
        for event in events:
            outbox_event = OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type=event.event_type,
                payload=json.dumps(event.to_dict()),
                aggregate_id=command.capability_family_id,
            )
            self._outbox_repo.save_event(outbox_event)

        return ScoringResult(
            success=True,
            health_score_id=health_score.health_score_id,
            previous_score=previous_score,
            new_score=health_score.current_score,
            events=events,
            occ_retries=attempt,
        )

    def _build_events(
        self,
        health_score: CapabilityHealthScore,
        previous_score: float,
        command: ScoringCommand,
        is_new: bool,
    ) -> List:
        """Build domain events for this scoring transaction."""
        events = []

        # Health score updated event
        events.append(
            CapabilityHealthScoreUpdatedEvent(
                event_id=str(uuid.uuid4()),
                health_score_id=health_score.health_score_id,
                capability_family_id=command.capability_family_id,
                previous_score=previous_score,
                new_score=health_score.current_score,
                score_components=[
                    {
                        "name": c.component_name,
                        "score": c.component_score,
                        "weight": c.weight,
                    }
                    for c in command.components
                ],
                evaluation_id=command.evaluation_id,
                algorithm_version=command.algorithm_version,
                updated_at=datetime.utcnow().isoformat(),
            )
        )

        # ADR-138: Governance events
        if health_score.consecutive_low_scores >= SUSPEND_THRESHOLD:
            events.append(
                GovernanceCapabilitySuspendedEvent(
                    event_id=str(uuid.uuid4()),
                    capability_family_id=command.capability_family_id,
                    capability_urn=command.capability_urn,
                    consecutive_low_scores=health_score.consecutive_low_scores,
                    threshold=SUSPEND_THRESHOLD,
                    reason=f"Consecutive low scores ({health_score.consecutive_low_scores}) >= threshold ({SUSPEND_THRESHOLD})",
                    suspended_at=datetime.utcnow().isoformat(),
                )
            )

        if health_score.consecutive_high_scores >= UNSUSPEND_THRESHOLD:
            events.append(
                GovernanceCapabilityUnsuspendedEvent(
                    event_id=str(uuid.uuid4()),
                    capability_family_id=command.capability_family_id,
                    capability_urn=command.capability_urn,
                    consecutive_high_scores=health_score.consecutive_high_scores,
                    threshold=UNSUSPEND_THRESHOLD,
                    reason=f"Consecutive high scores ({health_score.consecutive_high_scores}) >= threshold ({UNSUSPEND_THRESHOLD})",
                    unsuspended_at=datetime.utcnow().isoformat(),
                )
            )

        return events
