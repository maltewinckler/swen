"""Remove bank credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.banking.repositories import BankCredentialRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class DeleteCredentialsCommand:
    """Command to delete bank credentials."""

    def __init__(
        self,
        credential_repository: BankCredentialRepository,
        uow: UnitOfWork,
    ):
        self._credential_repo = credential_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DeleteCredentialsCommand:
        return cls(
            credential_repository=factory.credential_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self, blz: str) -> bool:
        async with self._uow:
            return await self._credential_repo.delete(blz)
