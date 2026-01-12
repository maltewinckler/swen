"""List credentials query - retrieve bank credentials for display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.value_objects import BankCredentials

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class CredentialInfo:
    """Credential information for display."""

    credential_id: str
    blz: str
    label: str


@dataclass
class CredentialListResult:
    """Result of listing credentials."""

    credentials: list[CredentialInfo]
    total_count: int


class ListCredentialsQuery:
    """Query to list bank credentials."""

    def __init__(self, credential_repository: BankCredentialRepository):
        self._credential_repo = credential_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListCredentialsQuery:
        return cls(credential_repository=factory.credential_repository())

    async def execute(
        self,
    ) -> CredentialListResult:
        credential_tuples = await self._credential_repo.find_all()
        credentials = [
            CredentialInfo(credential_id=cred_id, blz=blz, label=label or "")
            for cred_id, blz, label in credential_tuples
        ]
        return CredentialListResult(
            credentials=credentials,
            total_count=len(credentials),
        )

    async def find_by_bank_code(self, bank_code: str) -> Optional[BankCredentials]:
        return await self._credential_repo.find_by_blz(bank_code)

    async def get_tan_settings(
        self,
        bank_code: str,
    ) -> tuple[Optional[str], Optional[str]]:
        return await self._credential_repo.get_tan_settings(bank_code)

    async def delete(self, bank_code: str) -> bool:
        return await self._credential_repo.delete(bank_code)
