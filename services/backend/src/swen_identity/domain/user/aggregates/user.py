"""User aggregate for identity concerns only."""

from datetime import datetime
from typing import Union
from uuid import UUID, uuid4

from swen.domain.shared.time import utc_now
from swen_identity.domain.user.value_objects import UserRole
from swen_identity.domain.user.value_objects.email import Email


class User:
    """
    User aggregate root.

    Manages user identity only. Preferences/settings are handled separately
    by the swen.domain.settings module.
    """

    def __init__(
        self,
        email: Union[str, Email],
        role: Union[str, UserRole] = UserRole.USER,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self._email = email if isinstance(email, Email) else Email(email)
        self._id = id or uuid4()
        self._role = role if isinstance(role, UserRole) else UserRole(role)
        self._created_at = created_at or utc_now()
        self._updated_at = updated_at or utc_now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def email(self) -> str:
        return self._email.value

    @property
    def email_obj(self) -> Email:
        return self._email

    @property
    def role(self) -> UserRole:
        return self._role

    @property
    def is_admin(self) -> bool:
        return self._role == UserRole.ADMIN

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def promote_to_admin(self) -> None:
        self._role = UserRole.ADMIN
        self._updated_at = utc_now()

    def demote_to_user(self) -> None:
        self._role = UserRole.USER
        self._updated_at = utc_now()

    @classmethod
    def create(
        cls,
        email: Union[str, Email],
        role: UserRole = UserRole.USER,
    ) -> "User":
        return cls(email=email, role=role)

    @classmethod
    def reconstitute(
        cls,
        id: UUID,
        email: Union[str, Email],
        role: Union[str, UserRole],
        created_at: datetime,
        updated_at: datetime,
    ) -> "User":
        return cls(
            id=id,
            email=email,
            role=role,
            created_at=created_at,
            updated_at=updated_at,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"User(id={self._id}, email={self._email.value})"
