"""Update dashboard widgets and settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

from swen.domain.user import AVAILABLE_WIDGETS, Email, User, UserRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class UpdateDashboardSettingsCommand:
    """Update dashboard widgets/settings; email can come from context."""

    def __init__(
        self,
        user_repo: UserRepository,
        email: Optional[str] = None,
    ) -> None:
        self._user_repo = user_repo
        self._email = email

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> UpdateDashboardSettingsCommand:
        return cls(
            user_repo=factory.user_repository(),
            email=factory.user_context.email,
        )

    async def execute(
        self,
        enabled_widgets: Optional[list[str]] = None,
        widget_settings: Optional[dict[str, dict[str, Any]]] = None,
        email: Optional[Union[str, Email]] = None,
    ) -> User:
        resolved_email = email or self._email
        if not resolved_email:
            msg = "Email must be provided either at construction or execution"
            raise ValueError(msg)

        if enabled_widgets is not None:
            invalid_widgets = set(enabled_widgets) - set(AVAILABLE_WIDGETS.keys())
            if invalid_widgets:
                msg = f"Invalid widget IDs: {invalid_widgets}"
                raise ValueError(msg)

        if widget_settings is not None:
            invalid_settings = set(widget_settings.keys()) - set(
                AVAILABLE_WIDGETS.keys(),
            )
            if invalid_settings:
                msg = f"Widget settings reference invalid widgets: {invalid_settings}"
                raise ValueError(msg)

        if enabled_widgets is None and widget_settings is None:
            msg = "At least one of enabled_widgets or widget_settings must be specified"
            raise ValueError(msg)

        user = await self._user_repo.get_or_create_by_email(resolved_email)

        user.update_dashboard_settings(
            enabled_widgets=enabled_widgets,
            widget_settings=widget_settings,
        )

        await self._user_repo.save(user)
        return user


class ResetDashboardSettingsCommand:
    """Reset dashboard settings to defaults."""

    def __init__(
        self,
        user_repo: UserRepository,
        email: Optional[str] = None,
    ):
        self._user_repo = user_repo
        self._email = email

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> ResetDashboardSettingsCommand:
        return cls(
            user_repo=factory.user_repository(),
            email=factory.user_context.email,
        )

    async def execute(self, email: Optional[Union[str, Email]] = None) -> User:
        resolved_email = email or self._email
        if not resolved_email:
            msg = "Email must be provided either at construction or execution"
            raise ValueError(msg)

        user = await self._user_repo.get_or_create_by_email(resolved_email)
        user.reset_dashboard_settings()
        await self._user_repo.save(user)
        return user
