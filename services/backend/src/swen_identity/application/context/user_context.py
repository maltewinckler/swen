"""User context for request-scoped user identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from swen_identity.domain.user import User


@dataclass(frozen=True)
class UserContext:
    """Immutable context for the current authenticated user."""

    user_id: UUID
    email: str
    is_admin: bool = False

    @classmethod
    def create(cls, user: User) -> UserContext:
        return cls(user_id=user.id, email=user.email, is_admin=user.is_admin)

    @classmethod
    def from_values(
        cls,
        user_id: UUID,
        email: str,
        is_admin: bool = False,
    ) -> UserContext:
        return cls(user_id=user_id, email=email, is_admin=is_admin)

    def __str__(self) -> str:
        return f"UserContext({self.email})"

    def __repr__(self) -> str:
        return (
            f"UserContext(user_id={self.user_id}, "
            f"email={self.email!r}, is_admin={self.is_admin})"
        )
