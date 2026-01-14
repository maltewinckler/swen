"""IdentityAdapter - translates swen_identity types to swen's ports.

This is the ONLY place in swen's infrastructure that imports from swen_identity
(except for the presentation layer which wires everything together).
"""

from swen.application.ports.identity import CurrentUser

# This adapter is the anti-corruption layer boundary
from swen_identity import UserContext


class IdentityAdapter:
    """Adapts swen_identity types to swen's port interfaces."""

    @staticmethod
    def to_current_user(current_user: UserContext) -> CurrentUser:
        """Convert swen_identity.UserContext to swen's CurrentUser port."""
        return CurrentUser(
            user_id=current_user.user_id,
            email=current_user.email,
            is_admin=current_user.is_admin,
        )
