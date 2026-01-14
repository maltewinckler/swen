"""Abstract repository for user settings."""

from abc import ABC, abstractmethod

from swen.domain.settings.aggregates import UserSettings


class UserSettingsRepository(ABC):
    """Repository interface for UserSettings aggregate.

    This repository is user-scoped - all operations automatically apply to
    the current user without needing to pass user_id explicitly.
    """

    @abstractmethod
    async def get_or_create(self) -> UserSettings:
        """Get user settings, creating defaults if not exists."""

    @abstractmethod
    async def find(self) -> UserSettings | None:
        """Find settings for current user, returns None if not exists."""

    @abstractmethod
    async def save(self, settings: UserSettings) -> None:
        """Save user settings."""

    @abstractmethod
    async def delete(self) -> bool:
        """Delete user settings. Returns True if deleted."""
