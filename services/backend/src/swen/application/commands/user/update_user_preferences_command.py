"""Update user preferences with partial fields."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from swen.domain.user import Email, User, UserRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class UpdateUserPreferencesCommand:
    """Update user preferences, resolving email from context when available."""

    def __init__(
        self,
        user_repo: UserRepository,
        email: Optional[str] = None,
    ):
        self._user_repo = user_repo
        self._email = email

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UpdateUserPreferencesCommand:
        return cls(
            user_repo=factory.user_repository(),
            email=factory.user_context.email,
        )

    async def execute(
        self,
        auto_post_transactions: Optional[bool] = None,
        default_currency: Optional[str] = None,
        show_draft_transactions: Optional[bool] = None,
        default_date_range_days: Optional[int] = None,
        email: Optional[Union[str, Email]] = None,
    ) -> User:
        resolved_email = email or self._email
        if not resolved_email:
            msg = "Email must be provided either at construction or execution"
            raise ValueError(msg)

        user = await self._user_repo.get_or_create_by_email(resolved_email)
        if all(
            v is None
            for v in [
                auto_post_transactions,
                default_currency,
                show_draft_transactions,
                default_date_range_days,
            ]
        ):
            msg = "At least one preference must be specified for update"
            raise ValueError(msg)

        user.update_preferences(
            auto_post_transactions=auto_post_transactions,
            default_currency=default_currency,
            show_draft_transactions=show_draft_transactions,
            default_date_range_days=default_date_range_days,
        )
        await self._user_repo.save(user)
        return user
