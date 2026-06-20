"""SchedulePolicy value object — Sprint-07 Wave-1."""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SchedulePolicy:
    """Defines when a review is due and when it becomes overdue.

    This is a value object embedded in ReviewCycle.
    Status is projection-derived, not stored here.
    """
    observation_window_days: int
    overdue_threshold_days: int
    review_due_date: str  # ISO datetime string
    auto_expire: bool = False

    def __post_init__(self):
        if self.observation_window_days <= 0:
            raise ValueError("observation_window_days must be positive.")
        if self.overdue_threshold_days <= 0:
            raise ValueError("overdue_threshold_days must be positive.")

    @classmethod
    def create(
        cls,
        observation_window_days: int,
        overdue_threshold_days: int,
        created_at: datetime,
        auto_expire: bool = False,
    ) -> "SchedulePolicy":
        """Factory that computes review_due_date from created_at + observation_window_days."""
        due_date = created_at + timedelta(days=observation_window_days)
        return cls(
            observation_window_days=observation_window_days,
            overdue_threshold_days=overdue_threshold_days,
            review_due_date=due_date.isoformat(),
            auto_expire=auto_expire,
        )

    @property
    def due_date(self) -> datetime:
        return datetime.fromisoformat(self.review_due_date)
