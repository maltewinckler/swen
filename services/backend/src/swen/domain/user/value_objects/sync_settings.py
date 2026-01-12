"""Sync settings value object.

Controls how transactions are imported and processed during bank sync
and manual transaction entry.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncSettings:
    """Settings controlling transaction sync behavior."""

    auto_post_transactions: bool = False
    default_currency: str = "EUR"

    def __post_init__(self) -> None:
        if not self.default_currency:
            msg = "default_currency cannot be empty"
            raise ValueError(msg)

        if len(self.default_currency) != 3:
            msg = f"default_currency must be 3 characters, got: {self.default_currency}"
            raise ValueError(msg)

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
