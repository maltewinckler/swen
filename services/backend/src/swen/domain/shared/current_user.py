"""CurrentUser — swen's representation of the authenticated user.

Defined in domain/shared so that domain services can depend on it directly
without reaching into the application layer.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CurrentUser:
    """Immutable representation of the current authenticated user.

    This is swen's own type — it has no dependency on swen_identity.
    The adapter layer translates from swen_identity.UserContext to this.
    """

    user_id: UUID
    email: str
    is_admin: bool = False

    def __str__(self) -> str:
        return f"CurrentUser({self.email})"

    def __repr__(self) -> str:
        return (
            f"CurrentUser(user_id={self.user_id}, "
            f"email={self.email!r}, is_admin={self.is_admin})"
        )
