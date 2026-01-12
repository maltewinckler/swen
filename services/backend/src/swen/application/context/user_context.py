"""User context for request-scoped user identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from swen.domain.user.aggregates import User


@dataclass(frozen=True)
class UserContext:
    """
    Immutable context for the current authenticated user.

    This is created once per request/command execution and passed to
    repositories. Repositories use the user_id to automatically filter
    all queries to the current user's data.
    """

    user_id: UUID
    email: str

    @classmethod
    def create(cls, user: User) -> UserContext:
        return cls(user_id=user.id, email=user.email)

    @classmethod
    def from_values(cls, user_id: UUID, email: str) -> UserContext:
        return cls(user_id=user_id, email=email)

    def __str__(self) -> str:
        return f"UserContext({self.email})"

    def __repr__(self) -> str:
        return f"UserContext(user_id={self.user_id}, email={self.email!r})"
