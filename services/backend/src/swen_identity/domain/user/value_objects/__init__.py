"""Value objects for the user domain having identity concerns only."""

from swen_identity.domain.user.value_objects.email import Email
from swen_identity.domain.user.value_objects.user_role import UserRole

__all__ = [
    "Email",
    "UserRole",
]
