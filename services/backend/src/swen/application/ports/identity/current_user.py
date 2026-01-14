"""CurrentUser - swen's view of the authenticated user.

This is a port that defines what swen needs from the identity system.
The actual implementation is provided by an adapter that translates
from swen_identity.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CurrentUser:
    """Immutable representation of the current authenticated user.

    This is swen's own type - it has no dependency on swen_identity.
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
