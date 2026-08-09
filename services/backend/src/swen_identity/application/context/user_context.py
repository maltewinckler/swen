"""User context for request-scoped user identity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from swen_identity.domain.value_objects import UserRole

if TYPE_CHECKING:
    from swen_identity.domain import User


class UserContext(BaseModel):
    """The public, immutable representation of the current authenticated user."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    email: str
    role: UserRole
    created_at: datetime

    @computed_field
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @classmethod
    def create(cls, user: User) -> UserContext:
        return cls(
            user_id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        )

    def __str__(self) -> str:
        return f"UserContext({self.email})"

    def __repr__(self) -> str:
        return (
            f"UserContext(user_id={self.user_id}, "
            f"email={self.email!r}, role={self.role!r})"
        )
