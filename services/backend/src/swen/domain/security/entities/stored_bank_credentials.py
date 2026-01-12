"""Stored bank credentials entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class StoredBankCredentials:
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
    - endpoint: Public URL (needed for queries)
    """

    id: str
    user_id: UUID

    blz: str
    endpoint: str
    username_encrypted: bytes
    pin_encrypted: bytes
    encryption_version: int
    label: Optional[str]
    is_active: bool
    tan_method: Optional[str]  # ID code for TAN method
    tan_medium: Optional[str]  # name for the TAN medium (SecureGo)

    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]

    def __repr__(self) -> str:
        return (
            f"StoredBankCredentials(id={self.id}, user_id={self.user_id}, "
            f"blz={self.blz}, label={self.label}, is_active={self.is_active})"
        )
