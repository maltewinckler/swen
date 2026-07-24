"""Display settings value object."""

from pydantic import BaseModel, ConfigDict, Field


class DisplaySettings(BaseModel):
    """Settings controlling data display and presentation."""

    model_config = ConfigDict(frozen=True, validate_assignment=True)

    show_draft_transactions: bool = True
    default_date_range_days: int = Field(default=30, ge=1, le=3650)

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
