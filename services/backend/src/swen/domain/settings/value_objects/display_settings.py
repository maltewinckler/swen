"""Display settings value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplaySettings:
    """Settings controlling data display and presentation."""

    show_draft_transactions: bool = True
    default_date_range_days: int = 30

    def __post_init__(self):
        if self.default_date_range_days < 1:
            msg = (
                "default_date_range_days must be positive, "
                f"got: {self.default_date_range_days}"
            )
            raise ValueError(msg)

        if self.default_date_range_days > 3650:  # 10 years
            msg = f"default_date_range_days too large: {self.default_date_range_days}"
            raise ValueError(msg)

    @classmethod
    def default(cls) -> "DisplaySettings":
        return cls()

    def with_show_drafts(self, show_drafts: bool) -> "DisplaySettings":
        return DisplaySettings(
            show_draft_transactions=show_drafts,
            default_date_range_days=self.default_date_range_days,
        )

    def with_date_range(self, days: int) -> "DisplaySettings":
        return DisplaySettings(
            show_draft_transactions=self.show_draft_transactions,
            default_date_range_days=days,
        )
