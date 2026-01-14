"""SQLAlchemy implementation of UserRepository."""

import logging
from typing import Union
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from swen_identity.domain.user import (
    Email,
    EmailAlreadyExistsError,
    User,
    UserRepository,
)
from swen_identity.infrastructure.persistence.sqlalchemy.models import UserModel

logger = logging.getLogger(__name__)


class UserRepositorySQLAlchemy(UserRepository):
    """SQLAlchemy implementation of the UserRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, user_id: UUID) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._map_to_domain(model)

    async def find_by_email(self, email: Union[str, Email]) -> User | None:
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

    async def save(self, user: User) -> None:
        existing = await self._find_model_by_id(user.id)

        try:
            if existing:
                self._update_model(existing, user)
                logger.debug("Updated user: %s", user.id)
            else:
                model = self._map_to_model(user)
                self._session.add(model)
                logger.info("Created user: %s (email: %s)", user.id, user.email)

            await self._session.flush()
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) or "unique" in str(e).lower():
                raise EmailAlreadyExistsError(user.email) from e
            raise

    async def get_or_create_by_email(self, email: Union[str, Email]) -> User:
        email_obj = email if isinstance(email, Email) else Email(email)
        user = await self.find_by_email(email_obj)

        if user is not None:
            return user

        logger.info("Creating new user for email: %s", email_obj.value)
        new_user = User.create(email_obj)
        await self.save(new_user)

        return new_user

    async def delete(self, user_id: UUID) -> None:
        model = await self._find_model_by_id(user_id)

        if model:
            await self._session.delete(model)
            await self._session.flush()
            logger.info("Deleted user: %s", user_id)

    async def delete_with_all_data(self, user_id: UUID) -> None:
        await self.delete(user_id)
        logger.info("Deleted user and all associated data: %s", user_id)

    async def count(self) -> int:
        stmt = select(func.count()).select_from(UserModel)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_all(self) -> list[User]:
        stmt = select(UserModel).order_by(UserModel.created_at)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._map_to_domain(model) for model in models]

    async def _find_model_by_id(self, user_id: UUID) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _map_to_domain(self, model: UserModel) -> User:
        return User.reconstitute(
            id=model.id,
            email=model.email,
            role=model.role,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _map_to_model(self, user: User) -> UserModel:
        return UserModel(
            id=user.id,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _update_model(self, model: UserModel, user: User) -> None:
        model.email = user.email
        model.role = user.role.value
        model.updated_at = user.updated_at
