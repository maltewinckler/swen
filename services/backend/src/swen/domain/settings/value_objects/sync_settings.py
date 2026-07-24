"""Sync settings value object.

Controls how transactions are imported and processed during bank sync
and manual transaction entry.
"""

from pydantic import BaseModel, ConfigDict, Field

CURRENCY_CODE_LENGTH = 3


class SyncSettings(BaseModel):
    """Settings controlling transaction sync behavior."""

    model_config = ConfigDict(frozen=True, validate_assignment=True)

    auto_post_transactions: bool = False
    default_currency: str = Field(default="EUR", min_length=3, max_length=3)

    @classmethod
    def default(cls) -> "SyncSettings":
        return cls()

    def with_auto_post(self, auto_post: bool) -> "SyncSettings":
        return SyncSettings(
            auto_post_transactions=auto_post,
            default_currency=self.default_currency,
        )

    def with_currency(self, currency: str) -> "SyncSettings":
        return SyncSettings(
            auto_post_transactions=self.auto_post_transactions,
            default_currency=currency.upper(),
        )
