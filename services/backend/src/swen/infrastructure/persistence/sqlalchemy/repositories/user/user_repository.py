"""SQLAlchemy implementation of UserRepository."""

import logging
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.user import (
    AISettings,
    DashboardSettings,
    DisplaySettings,
    Email,
    EmailAlreadyExistsError,
    SyncSettings,
    User,
    UserPreferences,
    UserRepository,
)
from swen.infrastructure.persistence.sqlalchemy.models.user import UserModel

logger = logging.getLogger(__name__)


class UserRepositorySQLAlchemy(UserRepository):
    """SQLAlchemy implementation of the UserRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._map_to_domain(model)

    async def find_by_email(self, email: Union[str, Email]) -> Optional[User]:
        # Normalize email for lookup
        email_value = email.value if isinstance(email, Email) else Email(email).value

        stmt = select(UserModel).where(UserModel.email == email_value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._map_to_domain(model)

    async def exists_by_email(self, email: Union[str, Email]) -> bool:
        user = await self.find_by_email(email)
        return user is not None

    async def save(self, user: User):
        # Check if user exists
        existing = await self._find_model_by_id(user.id)

        try:
            if existing:
                # Update existing record
                self._update_model(existing, user)
                logger.debug("Updated user: %s", user.id)
            else:
                # Create new record
                model = self._map_to_model(user)
                self._session.add(model)
                logger.info("Created user: %s (email: %s)", user.id, user.email)

            await self._session.flush()
        except IntegrityError as e:
            # Handle unique constraint violation on email
            if "UNIQUE constraint failed" in str(e) or "unique" in str(e).lower():
                raise EmailAlreadyExistsError(user.email) from e
            raise

    async def get_or_create_by_email(self, email: Union[str, Email]) -> User:
        # Ensure we have an Email value object for validation
        email_obj = email if isinstance(email, Email) else Email(email)

        # Try to find existing user
        user = await self.find_by_email(email_obj)

        if user is not None:
            return user

        # Create new user with default preferences
        logger.info("Creating new user for email: %s", email_obj.value)
        new_user = User.create(email_obj)
        await self.save(new_user)

        return new_user

    async def delete(self, user_id: UUID):
        model = await self._find_model_by_id(user_id)

        if model:
            await self._session.delete(model)
            await self._session.flush()
            logger.info("Deleted user: %s", user_id)

    async def delete_with_all_data(self, user_id: UUID):
        # The actual cascade deletion happens via database FK constraints
        # We just delete the user record here
        await self.delete(user_id)
        logger.info("Deleted user and all associated data: %s", user_id)

    async def _find_model_by_id(self, user_id: UUID) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _map_to_domain(self, model: UserModel) -> User:
        # Reconstruct value objects
        sync_settings = SyncSettings(
            auto_post_transactions=model.auto_post_transactions,
            default_currency=model.default_currency,
        )

        display_settings = DisplaySettings(
            show_draft_transactions=model.show_draft_transactions,
            default_date_range_days=model.default_date_range_days,
        )

        # Reconstruct dashboard settings from JSON columns (or use defaults)
        enabled_widgets = model.dashboard_enabled_widgets
        widget_settings = model.dashboard_widget_settings

        if enabled_widgets is not None:
            dashboard_settings = DashboardSettings(
                enabled_widgets=tuple(enabled_widgets),
                widget_settings=widget_settings or {},
            )
        else:
            # Use defaults for users without dashboard settings
            dashboard_settings = DashboardSettings()

        # Reconstruct AI settings (with fallback to defaults for existing users)
        min_conf = model.ai_min_confidence
        ai_settings = AISettings(
            enabled=model.ai_enabled if model.ai_enabled is not None else True,
            model_name=model.ai_model_name or "qwen2.5:3b",
            min_confidence=min_conf,
        )

        preferences = UserPreferences(
            sync_settings=sync_settings,
            display_settings=display_settings,
            dashboard_settings=dashboard_settings,
            ai_settings=ai_settings,
        )

        return User.reconstitute(
            id=model.id,
            email=model.email,
            preferences=preferences,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _map_to_model(self, user: User) -> UserModel:
        dashboard = user.preferences.dashboard_settings
        ai = user.preferences.ai_settings
        return UserModel(
            id=user.id,
            email=user.email,
            auto_post_transactions=user.preferences.sync_settings.auto_post_transactions,
            default_currency=user.preferences.sync_settings.default_currency,
            show_draft_transactions=user.preferences.display_settings.show_draft_transactions,
            default_date_range_days=user.preferences.display_settings.default_date_range_days,
            dashboard_enabled_widgets=list(dashboard.enabled_widgets),
            dashboard_widget_settings=dashboard.widget_settings,
            ai_enabled=ai.enabled,
            ai_model_name=ai.model_name,
            ai_min_confidence=ai.min_confidence,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _update_model(self, model: UserModel, user: User):
        # Note: id should never change. Email can be updated if needed.
        model.email = user.email
        model.auto_post_transactions = (
            user.preferences.sync_settings.auto_post_transactions
        )
        model.default_currency = user.preferences.sync_settings.default_currency
        model.show_draft_transactions = (
            user.preferences.display_settings.show_draft_transactions
        )
        model.default_date_range_days = (
            user.preferences.display_settings.default_date_range_days
        )
        # Update dashboard settings
        dashboard = user.preferences.dashboard_settings
        model.dashboard_enabled_widgets = list(dashboard.enabled_widgets)
        model.dashboard_widget_settings = dashboard.widget_settings
        # Update AI settings
        ai = user.preferences.ai_settings
        model.ai_enabled = ai.enabled
        model.ai_model_name = ai.model_name
        model.ai_min_confidence = ai.min_confidence
        model.updated_at = user.updated_at
