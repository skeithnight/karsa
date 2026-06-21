"""ConvictionScore value object -- Sprint-13. ADR-140."""

from dataclasses import dataclass

from karsa.investment_workflow.domain.value_objects.enums import ConvictionLevel


@dataclass(frozen=True)
class ConvictionScore:
    """Conviction scoring for investment decisions.

    Maps analyst agreement to conviction levels:
    - STRONG: 3-4 analysts agree positively
    - MEDIUM: 2 analysts agree positively
    - WEAK: 1 analyst agrees (contrarian call)
    """

    level: str  # ConvictionLevel value
    numeric_score: float  # 0.0-10.0
    analyst_agreement: int  # how many analysts agree (0-5)

    def __post_init__(self) -> None:
        if not 0.0 <= self.numeric_score <= 10.0:
            raise ValueError(
                f"numeric_score must be 0.0-10.0, got {self.numeric_score}"
            )
        if not 0 <= self.analyst_agreement <= 5:
            raise ValueError(
                f"analyst_agreement must be 0-5, got {self.analyst_agreement}"
            )
        valid_levels = {e.value for e in ConvictionLevel}
        if self.level not in valid_levels:
            raise ValueError(
                f"level must be one of {valid_levels}, got {self.level}"
            )

    @classmethod
    def from_analyst_scores(cls, scores: list) -> "ConvictionScore":
        """Compute conviction from analyst scores.

        Positive = score >= 6.0. Agreement = count of positive scores.
        """
        positive_count = sum(1 for s in scores if s >= 6.0)
        avg_score = sum(scores) / len(scores) if scores else 0.0

        if positive_count >= 3:
            level = ConvictionLevel.STRONG.value
        elif positive_count >= 2:
            level = ConvictionLevel.MEDIUM.value
        else:
            level = ConvictionLevel.WEAK.value

        return cls(
            level=level,
            numeric_score=round(avg_score, 1),
            analyst_agreement=positive_count,
        )
