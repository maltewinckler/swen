"""Unit tests for User aggregate."""

import time
from datetime import datetime, timezone
from uuid import UUID

import pytest

from swen.domain.user import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    Email,
    InvalidEmailError,
    User,
    UserNotFoundError,
    UserPreferences,
    UserRole,
)


class TestUser:
    """Tests for User aggregate."""

    def test_create_generates_random_uuid(self):
        """User.create generates a random UUID4 for ID."""
        user = User.create("test@example.com")

        assert isinstance(user.id, UUID)
        assert user.email == "test@example.com"
        assert user.preferences == UserPreferences()

    def test_create_generates_unique_ids(self):
        """Each User.create call generates a unique ID."""
        user1 = User.create("test@example.com")
        user2 = User.create("test@example.com")

        # Same email but different IDs (random UUID4)
        assert user1.id != user2.id
        assert user1.email == user2.email

    def test_create_with_email_object(self):
        """User.create accepts Email value object."""
        email = Email("test@example.com")
        user = User.create(email)

        assert isinstance(user.id, UUID)
        assert user.email == "test@example.com"

    def test_email_normalized(self):
        """Email is normalized to lowercase."""
        user = User.create("TEST@EXAMPLE.COM")

        assert user.email == "test@example.com"

    def test_create_with_invalid_email_raises(self):
        """User.create raises InvalidEmailError for invalid email."""
        with pytest.raises(InvalidEmailError):
            User.create("not-an-email")

    def test_update_preferences(self):
        """update_preferences modifies user preferences."""
        user = User.create("test@example.com")
        original_updated_at = user.updated_at

        user.update_preferences(auto_post_transactions=True)

        assert user.preferences.sync_settings.auto_post_transactions is True
        assert user.updated_at >= original_updated_at

    def test_update_preferences_partial(self):
        """update_preferences only changes specified fields."""
        user = User.create("test@example.com")

        user.update_preferences(show_draft_transactions=False)

        assert user.preferences.display_settings.show_draft_transactions is False
        assert (
            user.preferences.sync_settings.auto_post_transactions is False
        )  # Unchanged

    def test_reset_preferences(self):
        """reset_preferences restores defaults."""
        user = User.create("test@example.com")
        user.update_preferences(
            auto_post_transactions=True,
            default_currency="USD",
            show_draft_transactions=False,
            default_date_range_days=90,
        )

        user.reset_preferences()

        assert user.preferences == UserPreferences()

    def test_equality_based_on_id(self):
        """Users are equal if they have the same ID."""
        from uuid import uuid4

        user_id = uuid4()
        user1 = User(
            id=user_id,
            email="test@example.com",
            preferences=UserPreferences(),
        )
        user2 = User(
            id=user_id,
            email="test@example.com",
            preferences=UserPreferences(),
        )

        assert user1 == user2

    def test_inequality_different_ids(self):
        """Users with different IDs are not equal, even with same email."""
        user1 = User.create("test@example.com")
        user2 = User.create("test@example.com")

        # Different random IDs means not equal
        assert user1 != user2

    def test_inequality_different_emails(self):
        """Users with different emails (and thus different IDs) are not equal."""
        user1 = User.create("alice@example.com")
        user2 = User.create("bob@example.com")

        assert user1 != user2

    def test_hash_based_on_id(self):
        """Users with same ID have same hash."""
        from uuid import uuid4

        user_id = uuid4()
        user1 = User(
            id=user_id,
            email="test@example.com",
            preferences=UserPreferences(),
        )
        user2 = User(
            id=user_id,
            email="test@example.com",
            preferences=UserPreferences(),
        )

        assert hash(user1) == hash(user2)

    def test_timestamps_set_on_creation(self):
        """created_at and updated_at set on creation."""
        before = datetime.now(tz=timezone.utc)
        user = User.create("test@example.com")
        after = datetime.now(tz=timezone.utc)

        assert before <= user.created_at <= after
        assert before <= user.updated_at <= after

    def test_updated_at_changes_on_preference_update(self):
        """updated_at changes when preferences are updated."""
        user = User.create("test@example.com")
        original = user.updated_at

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        user.update_preferences(auto_post_transactions=True)

        assert user.updated_at > original

    def test_repr(self):
        """User has useful string representation."""
        user = User.create("test@example.com")
        repr_str = repr(user)

        assert "User" in repr_str
        assert "test@example.com" in repr_str

    def test_email_obj_property(self):
        """email_obj returns the Email value object."""
        user = User.create("test@example.com")

        assert isinstance(user.email_obj, Email)
        assert user.email_obj.value == "test@example.com"

    def test_reconstitute_with_id(self):
        """reconstitute restores user with specific ID."""
        from uuid import uuid4

        user_id = uuid4()
        created = datetime(2023, 1, 1, tzinfo=timezone.utc)
        updated = datetime(2023, 6, 1, tzinfo=timezone.utc)

        user = User.reconstitute(
            id=user_id,
            email="test@example.com",
            preferences=UserPreferences(),
            role=UserRole.USER,
            created_at=created,
            updated_at=updated,
        )

        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.created_at == created
        assert user.updated_at == updated

    def test_create_with_default_role(self):
        """User.create defaults to USER role."""
        user = User.create("test@example.com")

        assert user.role == UserRole.USER
        assert user.is_admin is False

    def test_create_with_admin_role(self):
        """User.create can create an admin."""
        user = User.create("admin@example.com", role=UserRole.ADMIN)

        assert user.role == UserRole.ADMIN
        assert user.is_admin is True

    def test_promote_to_admin(self):
        """promote_to_admin changes role to ADMIN."""
        user = User.create("test@example.com")
        original_updated_at = user.updated_at

        time.sleep(0.01)
        user.promote_to_admin()

        assert user.role == UserRole.ADMIN
        assert user.is_admin is True
        assert user.updated_at > original_updated_at

    def test_demote_to_user(self):
        """demote_to_user changes role to USER."""
        user = User.create("admin@example.com", role=UserRole.ADMIN)
        original_updated_at = user.updated_at

        time.sleep(0.01)
        user.demote_to_user()

        assert user.role == UserRole.USER
        assert user.is_admin is False
        assert user.updated_at > original_updated_at

    def test_reconstitute_with_string_role(self):
        """reconstitute handles string role conversion."""
        from uuid import uuid4

        user_id = uuid4()
        created = datetime(2023, 1, 1, tzinfo=timezone.utc)
        updated = datetime(2023, 6, 1, tzinfo=timezone.utc)

        user = User.reconstitute(
            id=user_id,
            email="admin@example.com",
            preferences=UserPreferences(),
            role="admin",  # String instead of UserRole enum
            created_at=created,
            updated_at=updated,
        )

        assert user.role == UserRole.ADMIN
        assert user.is_admin is True

    def test_reconstitute_with_enum_role(self):
        """reconstitute works with UserRole enum."""
        from uuid import uuid4

        user_id = uuid4()
        created = datetime(2023, 1, 1, tzinfo=timezone.utc)
        updated = datetime(2023, 6, 1, tzinfo=timezone.utc)

        user = User.reconstitute(
            id=user_id,
            email="test@example.com",
            preferences=UserPreferences(),
            role=UserRole.USER,
            created_at=created,
            updated_at=updated,
        )

        assert user.role == UserRole.USER


class TestUserRole:
    """Tests for UserRole enum."""

    def test_user_role_values(self):
        """UserRole has correct values."""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"

    def test_user_role_from_string(self):
        """UserRole can be created from string."""
        assert UserRole("user") == UserRole.USER
        assert UserRole("admin") == UserRole.ADMIN

    def test_user_role_invalid_raises(self):
        """Invalid role string raises ValueError."""
        with pytest.raises(ValueError):
            UserRole("superadmin")


class TestUserExceptions:
    """Tests for user domain exceptions."""

    def test_user_not_found_error(self):
        """UserNotFoundError contains user_id."""
        error = UserNotFoundError("123")
        assert error.user_id == "123"
        assert "123" in str(error)

    def test_cannot_delete_self_error(self):
        """CannotDeleteSelfError has correct message."""
        error = CannotDeleteSelfError()
        assert "delete" in str(error).lower()
        assert "own" in str(error).lower()

    def test_cannot_demote_self_error(self):
        """CannotDemoteSelfError has correct message."""
        error = CannotDemoteSelfError()
        assert "demote" in str(error).lower()


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email(self):
        """Valid email is accepted."""
        email = Email("test@example.com")
        assert email.value == "test@example.com"

    def test_normalized_to_lowercase(self):
        """Email is normalized to lowercase."""
        email = Email("TEST@EXAMPLE.COM")
        assert email.value == "test@example.com"

    def test_stripped_whitespace(self):
        """Whitespace is stripped."""
        email = Email("  test@example.com  ")
        assert email.value == "test@example.com"

    def test_empty_raises(self):
        """Empty email raises InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("")

    def test_invalid_format_raises(self):
        """Invalid format raises InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("not-an-email")

    def test_missing_domain_raises(self):
        """Missing domain raises InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("test@")

    def test_missing_tld_raises(self):
        """Missing TLD raises InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            Email("test@example")

    def test_str_returns_value(self):
        """str() returns the email value."""
        email = Email("test@example.com")
        assert str(email) == "test@example.com"
