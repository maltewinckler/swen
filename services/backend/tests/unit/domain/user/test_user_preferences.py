"""Unit tests for user preferences value objects."""

import pytest

from swen.domain.user.value_objects import (
    DisplaySettings,
    SyncSettings,
    UserPreferences,
)


class TestSyncSettings:
    """Tests for SyncSettings value object."""

    def test_default_values(self):
        """Default settings should be conservative."""
        settings = SyncSettings()

        assert settings.auto_post_transactions is False
        assert settings.default_currency == "EUR"

    def test_custom_values(self):
        """Can create with custom values."""
        settings = SyncSettings(
            auto_post_transactions=True,
            default_currency="USD",
        )

        assert settings.auto_post_transactions is True
        assert settings.default_currency == "USD"

    def test_with_auto_post_returns_new_instance(self):
        """with_auto_post returns new instance, original unchanged."""
        original = SyncSettings()
        updated = original.with_auto_post(True)

        assert original.auto_post_transactions is False
        assert updated.auto_post_transactions is True
        assert original is not updated

    def test_with_currency_returns_new_instance(self):
        """with_currency returns new instance, original unchanged."""
        original = SyncSettings()
        updated = original.with_currency("usd")

        assert original.default_currency == "EUR"
        assert updated.default_currency == "USD"  # Should be uppercase
        assert original is not updated

    def test_invalid_currency_empty(self):
        """Empty currency should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SyncSettings(auto_post_transactions=False, default_currency="")

    def test_invalid_currency_length(self):
        """Currency must be 3 characters."""
        with pytest.raises(ValueError, match="must be 3 characters"):
            SyncSettings(auto_post_transactions=False, default_currency="US")


class TestDisplaySettings:
    """Tests for DisplaySettings value object."""

    def test_default_values(self):
        """Default settings show complete picture."""
        settings = DisplaySettings()

        assert settings.show_draft_transactions is True
        assert settings.default_date_range_days == 30

    def test_custom_values(self):
        """Can create with custom values."""
        settings = DisplaySettings(
            show_draft_transactions=False,
            default_date_range_days=90,
        )

        assert settings.show_draft_transactions is False
        assert settings.default_date_range_days == 90

    def test_with_show_drafts_returns_new_instance(self):
        """with_show_drafts returns new instance."""
        original = DisplaySettings()
        updated = original.with_show_drafts(False)

        assert original.show_draft_transactions is True
        assert updated.show_draft_transactions is False
        assert original is not updated

    def test_with_date_range_returns_new_instance(self):
        """with_date_range returns new instance."""
        original = DisplaySettings()
        updated = original.with_date_range(60)

        assert original.default_date_range_days == 30
        assert updated.default_date_range_days == 60
        assert original is not updated

    def test_invalid_date_range_zero(self):
        """Date range must be positive."""
        with pytest.raises(ValueError, match="must be positive"):
            DisplaySettings(show_draft_transactions=True, default_date_range_days=0)

    def test_invalid_date_range_negative(self):
        """Date range cannot be negative."""
        with pytest.raises(ValueError, match="must be positive"):
            DisplaySettings(show_draft_transactions=True, default_date_range_days=-5)

    def test_invalid_date_range_too_large(self):
        """Date range cannot exceed 10 years."""
        with pytest.raises(ValueError, match="too large"):
            DisplaySettings(show_draft_transactions=True, default_date_range_days=4000)


class TestUserPreferences:
    """Tests for UserPreferences value object."""

    def test_default_values(self):
        """Default preferences combine defaults from both settings."""
        prefs = UserPreferences()

        assert prefs.sync_settings.auto_post_transactions is False
        assert prefs.sync_settings.default_currency == "EUR"
        assert prefs.display_settings.show_draft_transactions is True
        assert prefs.display_settings.default_date_range_days == 30

    def test_with_updates_partial(self):
        """with_updates allows partial updates."""
        original = UserPreferences()
        updated = original.with_updates(auto_post_transactions=True)

        # Only auto_post changed
        assert updated.sync_settings.auto_post_transactions is True
        # Others preserved
        assert updated.sync_settings.default_currency == "EUR"
        assert updated.display_settings.show_draft_transactions is True
        assert updated.display_settings.default_date_range_days == 30
        # Original unchanged
        assert original.sync_settings.auto_post_transactions is False

    def test_with_updates_multiple(self):
        """with_updates can update multiple fields."""
        original = UserPreferences()
        updated = original.with_updates(
            auto_post_transactions=True,
            default_currency="USD",
            show_draft_transactions=False,
            default_date_range_days=60,
        )

        assert updated.sync_settings.auto_post_transactions is True
        assert updated.sync_settings.default_currency == "USD"
        assert updated.display_settings.show_draft_transactions is False
        assert updated.display_settings.default_date_range_days == 60

    def test_with_updates_none_values_ignored(self):
        """None values should not change existing settings."""
        original = UserPreferences()
        updated = original.with_updates(
            auto_post_transactions=None,
            default_currency=None,
            show_draft_transactions=None,
            default_date_range_days=None,
        )

        # All values should remain defaults
        assert updated == original

    def test_immutability(self):
        """UserPreferences is immutable (frozen dataclass)."""
        prefs = UserPreferences()

        with pytest.raises(AttributeError):
            prefs.sync_settings = SyncSettings(True, "USD")  # type: ignore[misc]
