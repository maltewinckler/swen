from enum import Enum


class UserRole(str, Enum):
    """User roles (who will be admin and who not)."""

    USER = "user"
    ADMIN = "admin"
