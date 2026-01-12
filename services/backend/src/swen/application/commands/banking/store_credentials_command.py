"""Store bank credentials for automated sync."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from swen.domain.banking.exceptions import CredentialsAlreadyExistError
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.value_objects import BankCredentials

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class StoreCredentialsCommand:
    """Persist encrypted bank credentials for the current user."""

    def __init__(self, credential_repository: BankCredentialRepository):
        self._repo = credential_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> StoreCredentialsCommand:
        return cls(credential_repository=factory.credential_repository())

    async def execute(
        self,
        credentials: BankCredentials,
        label: Optional[str] = None,
        tan_method: Optional[str] = None,
        tan_medium: Optional[str] = None,
    ) -> str:
        existing = await self._repo.find_by_blz(credentials.blz)
        if existing:
            raise CredentialsAlreadyExistError(blz=credentials.blz)

        return await self._repo.save(
            credentials=credentials,
            label=label,
            tan_method=tan_method,
            tan_medium=tan_medium,
        )
