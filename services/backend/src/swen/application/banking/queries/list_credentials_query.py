"""List credentials query - retrieve bank credentials for display."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.banking.dtos import StoredCredentialDTO, StoredCredentialListDTO
from swen.domain.banking.repositories import BankCredentialRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class ListCredentialsQuery:
    """Query to list bank credentials."""

    def __init__(self, credential_repository: BankCredentialRepository):
        self._credential_repo = credential_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListCredentialsQuery:
        return cls(credential_repository=factory.credential_repository())

    async def execute(self) -> StoredCredentialListDTO:
        credential_tuples = await self._credential_repo.find_all()
        return StoredCredentialListDTO(
            credentials=[
                StoredCredentialDTO(credential_id=cred_id, blz=blz, label=label)
                for cred_id, blz, label in credential_tuples
            ]
        )
