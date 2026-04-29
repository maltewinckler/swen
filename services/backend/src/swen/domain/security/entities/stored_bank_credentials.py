"""Stored bank credentials entity."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StoredBankCredentials(BaseModel):
    """
    Entity representing encrypted banking credentials in storage.

    This is INTERNAL to the Security domain. It represents HOW we store
    credentials securely, but the Banking domain knows nothing about this.

    The Banking domain only knows about BankCredentials (the runtime representation).
    The Infrastructure layer (ACL) bridges between these two representations.

    Security Concerns:
    - username_encrypted: Binary blob of encrypted username
    - pin_encrypted: Binary blob of encrypted PIN
    - encryption_version: Allows key rotation and algorithm changes

    Non-Sensitive Fields:
    - blz: Public bank code (needed for queries)
    """

    model_config = ConfigDict(frozen=True)

    id: str
    user_id: UUID

    blz: str
    username_encrypted: bytes
    pin_encrypted: bytes
    encryption_version: int
    label: str | None
    is_active: bool
    tan_method: str | None
    tan_medium: str | None

    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None

    def __repr__(self) -> str:
        return (
            f"StoredBankCredentials(id={self.id}, user_id={self.user_id}, "
            f"blz={self.blz}, label={self.label}, is_active={self.is_active})"
        )
