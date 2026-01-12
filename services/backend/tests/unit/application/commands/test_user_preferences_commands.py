"""Unit tests for user preferences commands."""

from unittest.mock import AsyncMock

import pytest
from swen.application.commands import (
    ResetUserPreferencesCommand,
    UpdateUserPreferencesCommand,
)
from swen.domain.user import User, UserPreferences


TEST_EMAIL = "test@example.com"


@pytest.fixture
def mock_user():
    """Create a mock user with default preferences."""
    return User.create(TEST_EMAIL)


@pytest.fixture
def mock_user_repo(mock_user):
    """Create a mock user repository."""
    repo = AsyncMock()
    repo.get_or_create_by_email = AsyncMock(return_value=mock_user)
    repo.save = AsyncMock()
    return repo


class TestUpdateUserPreferencesCommand:
    """Tests for UpdateUserPreferencesCommand."""

    @pytest.mark.asyncio
    async def test_update_single_preference(self, mock_user_repo, mock_user):
        """Can update a single preference."""
        command = UpdateUserPreferencesCommand(mock_user_repo)

        result = await command.execute(
            email=TEST_EMAIL,
            auto_post_transactions=True,
        )

        assert result.preferences.sync_settings.auto_post_transactions is True
        mock_user_repo.save.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_update_multiple_preferences(self, mock_user_repo, mock_user):
        """Can update multiple preferences at once."""
        command = UpdateUserPreferencesCommand(mock_user_repo)

        result = await command.execute(
            email=TEST_EMAIL,
            auto_post_transactions=True,
            show_draft_transactions=False,
            default_currency="USD",
            default_date_range_days=60,
        )

        assert result.preferences.sync_settings.auto_post_transactions is True
        assert result.preferences.sync_settings.default_currency == "USD"
        assert result.preferences.display_settings.show_draft_transactions is False
        assert result.preferences.display_settings.default_date_range_days == 60

    @pytest.mark.asyncio
    async def test_no_updates_raises_error(self, mock_user_repo):
        """Raises ValueError if no updates provided."""
        command = UpdateUserPreferencesCommand(mock_user_repo)

        with pytest.raises(ValueError, match="At least one preference"):
            await command.execute(email=TEST_EMAIL)

    @pytest.mark.asyncio
    async def test_all_none_raises_error(self, mock_user_repo):
        """Raises ValueError if all values are None."""
        command = UpdateUserPreferencesCommand(mock_user_repo)

        with pytest.raises(ValueError, match="At least one preference"):
            await command.execute(
                email=TEST_EMAIL,
                auto_post_transactions=None,
                show_draft_transactions=None,
            )


class TestResetUserPreferencesCommand:
    """Tests for ResetUserPreferencesCommand."""

    @pytest.mark.asyncio
    async def test_reset_to_defaults(self, mock_user_repo, mock_user):
        """Resets all preferences to defaults."""
        # First modify user preferences
        mock_user.update_preferences(
            auto_post_transactions=True,
            default_currency="USD",
        )

        command = ResetUserPreferencesCommand(mock_user_repo)

        result = await command.execute(email=TEST_EMAIL)

        # Should be back to defaults
        assert result.preferences == UserPreferences()
        mock_user_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_creates_user_if_missing(self, mock_user_repo):
        """Creates user if it doesn't exist."""
        command = ResetUserPreferencesCommand(mock_user_repo)

        await command.execute(email=TEST_EMAIL)

        mock_user_repo.get_or_create_by_email.assert_called_once_with(TEST_EMAIL)
