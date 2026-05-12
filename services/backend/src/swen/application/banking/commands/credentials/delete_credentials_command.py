"""Remove bank credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.domain.banking.repositories import BankCredentialRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class DeleteCredentialsCommand:
    """Command to delete bank credentials."""

    def __init__(self, credential_repository: BankCredentialRepository):
        self._credential_repo = credential_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DeleteCredentialsCommand:
        return cls(credential_repository=factory.credential_repository())

    async def execute(self, blz: str) -> bool:
        return await self._credential_repo.delete(blz)
