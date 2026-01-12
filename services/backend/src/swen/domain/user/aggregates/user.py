"""User aggregate root."""

from datetime import datetime

from swen.domain.shared.time import utc_now
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from swen.domain.user.value_objects import (
    AISettings,
    DashboardSettings,
    UserPreferences,
)
from swen.domain.user.value_objects.email import Email


class User:
    """
    User aggregate root.

    Manages user identity and preferences. Each user is uniquely identified
    by a random UUID generated at creation time.
    """

    def __init__(
        self,
        email: Union[str, Email],
        preferences: UserPreferences,
        id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self._email = email if isinstance(email, Email) else Email(email)
        self._id = id if id is not None else uuid4()

        self._preferences = preferences
        self._created_at = created_at or utc_now()
        self._updated_at = updated_at or utc_now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def email(self) -> str:
        return self._email.value

    @property
    def email_obj(self) -> Email:
        return self._email

    @property
    def preferences(self) -> UserPreferences:
        return self._preferences

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_preferences(
        self,
        auto_post_transactions: Optional[bool] = None,
        default_currency: Optional[str] = None,
        show_draft_transactions: Optional[bool] = None,
        default_date_range_days: Optional[int] = None,
    ):
        # Only provided (non-None) values are updated; others are preserved.
        self._preferences = self._preferences.with_updates(
            auto_post_transactions=auto_post_transactions,
            default_currency=default_currency,
            show_draft_transactions=show_draft_transactions,
            default_date_range_days=default_date_range_days,
        )
        self._updated_at = utc_now()

    def reset_preferences(self):
        self._preferences = UserPreferences()
        self._updated_at = utc_now()

    def update_dashboard_settings(
        self,
        enabled_widgets: Optional[list[str]] = None,
        widget_settings: Optional[dict[str, dict[str, Any]]] = None,
    ):
        self._preferences = self._preferences.with_dashboard_updates(
            enabled_widgets=enabled_widgets,
            widget_settings=widget_settings,
        )
        self._updated_at = utc_now()

    def reset_dashboard_settings(self):
        self._preferences = UserPreferences(
            sync_settings=self._preferences.sync_settings,
            display_settings=self._preferences.display_settings,
            dashboard_settings=DashboardSettings(),
            ai_settings=self._preferences.ai_settings,
        )
        self._updated_at = utc_now()

    def update_ai_settings(
        self,
        enabled: Optional[bool] = None,
        model_name: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ):
        self._preferences = self._preferences.with_ai_updates(
            enabled=enabled,
            model_name=model_name,
            min_confidence=min_confidence,
        )
        self._updated_at = utc_now()

    def reset_ai_settings(self):
        self._preferences = UserPreferences(
            sync_settings=self._preferences.sync_settings,
            display_settings=self._preferences.display_settings,
            dashboard_settings=self._preferences.dashboard_settings,
            ai_settings=AISettings(),
        )
        self._updated_at = utc_now()

    @classmethod
    def create(cls, email: Union[str, Email]) -> "User":
        return cls(
            email=email,
            preferences=UserPreferences(),
            # id is None as default, so a new UUID4 will be generated
        )

    @classmethod
    def reconstitute(
        cls,
        id: UUID,
        email: Union[str, Email],
        preferences: UserPreferences,
        created_at: datetime,
        updated_at: datetime,
    ) -> "User":
        """Reconstitute a User from persisted data."""
        return cls(
            id=id,
            email=email,
            preferences=preferences,
            created_at=created_at,
            updated_at=updated_at,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"User(id={self._id}, email={self._email.value})"
