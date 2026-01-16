"""Unit tests for user settings commands."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from swen.application.commands.settings import (
    ResetUserSettingsCommand,
    UpdateUserSettingsCommand,
)
from swen.domain.settings import UserSettings

TEST_USER_ID = uuid4()


@pytest.fixture
def mock_settings():
    """Create mock user settings with defaults."""
    return UserSettings.default(TEST_USER_ID)


@pytest.fixture
def mock_settings_repo(mock_settings):
    """Create a mock settings repository."""
    repo = AsyncMock()
    repo.get_or_create = AsyncMock(return_value=mock_settings)
    repo.save = AsyncMock()
    return repo


class TestUpdateUserSettingsCommand:
    """Tests for UpdateUserSettingsCommand."""

    @pytest.mark.asyncio
    async def test_update_single_setting(self, mock_settings_repo, mock_settings):
        """Can update a single setting."""
        command = UpdateUserSettingsCommand(mock_settings_repo)

        result = await command.execute(auto_post_transactions=True)

        assert result.sync.auto_post_transactions is True
        mock_settings_repo.save.assert_called_once_with(mock_settings)

    @pytest.mark.asyncio
    async def test_update_multiple_settings(self, mock_settings_repo, mock_settings):
        """Can update multiple settings at once."""
        command = UpdateUserSettingsCommand(mock_settings_repo)

        result = await command.execute(
            auto_post_transactions=True,
            show_draft_transactions=False,
            default_currency="USD",
            default_date_range_days=60,
        )

        assert result.sync.auto_post_transactions is True
        assert result.sync.default_currency == "USD"
        assert result.display.show_draft_transactions is False
        assert result.display.default_date_range_days == 60

    @pytest.mark.asyncio
    async def test_no_updates_raises_error(self, mock_settings_repo):
        """Raises ValueError if no updates provided."""
        command = UpdateUserSettingsCommand(mock_settings_repo)

        with pytest.raises(ValueError, match="At least one setting"):
            await command.execute()

    @pytest.mark.asyncio
    async def test_update_dashboard_widgets(self, mock_settings_repo, mock_settings):
        """Can update dashboard widget settings."""
        command = UpdateUserSettingsCommand(mock_settings_repo)

        result = await command.execute(
            enabled_widgets=["summary-cards", "net-worth"],
        )

        assert list(result.dashboard.enabled_widgets) == ["summary-cards", "net-worth"]

    @pytest.mark.asyncio
    async def test_update_ai_settings(self, mock_settings_repo, mock_settings):
        """Can update AI settings."""
        command = UpdateUserSettingsCommand(mock_settings_repo)

        result = await command.execute(
            ai_enabled=False,
            ai_min_confidence=0.9,
        )

        assert result.ai.enabled is False
        assert result.ai.min_confidence == 0.9

    @pytest.mark.asyncio
    async def test_invalid_widget_raises_error(self, mock_settings_repo):
        """Raises ValueError for invalid widget IDs."""
        command = UpdateUserSettingsCommand(mock_settings_repo)

        with pytest.raises(ValueError, match="Invalid widget IDs"):
            await command.execute(enabled_widgets=["invalid-widget"])


class TestResetUserSettingsCommand:
    """Tests for ResetUserSettingsCommand."""

    @pytest.mark.asyncio
    async def test_reset_to_defaults(self, mock_settings_repo, mock_settings):
        """Resets all settings to defaults."""
        # First modify settings
        mock_settings.update_sync(auto_post_transactions=True, default_currency="USD")

        command = ResetUserSettingsCommand(mock_settings_repo)

        result = await command.execute()

        # Should be back to defaults
        assert result.sync.auto_post_transactions is False
        assert result.sync.default_currency == "EUR"
        mock_settings_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_creates_settings_if_missing(self, mock_settings_repo):
        """Creates settings if they don't exist."""
        command = ResetUserSettingsCommand(mock_settings_repo)

        await command.execute()

        mock_settings_repo.get_or_create.assert_called_once_with()
