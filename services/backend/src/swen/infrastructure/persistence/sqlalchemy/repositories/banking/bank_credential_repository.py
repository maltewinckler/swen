"""Bank credential repository - Anti-Corruption Layer (ACL)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.value_objects import BankCredentials
from swen.domain.security.entities import StoredBankCredentials
from swen.domain.security.repositories import StoredBankCredentialsRepository
from swen.domain.security.services import EncryptionService

if TYPE_CHECKING:
    from swen.application.context import UserContext


class BankCredentialRepositorySQLAlchemy(BankCredentialRepository):
    """
    Implementation of BankCredentialRepository using composition.

    This is the Anti-Corruption Layer (ACL) that orchestrates:
    1. StoredBankCredentialsRepository → Get encrypted data
    2. EncryptionService → Decrypt sensitive fields
    3. BankCredentials.from_plain() → Create Banking domain object
    """

    def __init__(
        self,
        stored_credentials_repo: StoredBankCredentialsRepository,
        encryption_service: EncryptionService,
        user_context: UserContext,
    ):
        self._stored_repo = stored_credentials_repo
        self._encryption = encryption_service
        self._user_id = user_context.user_id

    async def save(
        self,
        credentials: BankCredentials,
        label: Optional[str] = None,
        tan_method: Optional[str] = None,
        tan_medium: Optional[str] = None,
    ) -> str:
        # 1. Extract plain values
        username_plain = credentials.username.get_value()
        pin_plain = credentials.pin.get_value()

        # 2. Encrypt
        username_encrypted = self._encryption.encrypt(username_plain)
        pin_encrypted = self._encryption.encrypt(pin_plain)

        # 3. Create Security domain entity
        now = datetime.now(timezone.utc)
        stored = StoredBankCredentials(
            id=str(uuid4()),
            user_id=self._user_id,
            blz=credentials.blz,
            endpoint=credentials.endpoint,
            username_encrypted=username_encrypted,
            pin_encrypted=pin_encrypted,
            encryption_version=1,
            label=label,
            is_active=True,
            tan_method=tan_method,
            tan_medium=tan_medium,
            created_at=now,
            updated_at=now,
            last_used_at=None,
        )

        # 4. Save using StoredBankCredentialsRepository
        await self._stored_repo.save(stored)

        return stored.id

    async def find_by_blz(self, blz: str) -> Optional[BankCredentials]:
        # 1. Load encrypted credentials (Security domain)
        stored = await self._stored_repo.find_by_blz(blz)

        if not stored:
            return None

        # 2. Decrypt sensitive fields
        username_plain = self._encryption.decrypt(stored.username_encrypted)
        pin_plain = self._encryption.decrypt(stored.pin_encrypted)

        # 3. Create Banking domain object
        # This is the translation: Security storage → Banking domain
        return BankCredentials.from_plain(
            blz=stored.blz,
            username=username_plain,
            pin=pin_plain,
            endpoint=stored.endpoint,
        )

    async def find_all(self) -> list[tuple[str, str, str]]:
        stored_list = await self._stored_repo.find_all()

        return [(stored.id, stored.blz, stored.label or "") for stored in stored_list]

    async def delete(self, blz: str) -> bool:
        return await self._stored_repo.delete(blz)

    async def update_last_used(
        self,
        blz: str,
    ) -> None:
        await self._stored_repo.update_last_used(blz)

    async def get_tan_settings(self, blz: str) -> tuple[Optional[str], Optional[str]]:
        stored = await self._stored_repo.find_by_blz(blz)

        if not stored:
            return None, None

        return stored.tan_method, stored.tan_medium
