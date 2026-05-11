"""Store bank credentials for automated sync."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.banking import CredentialToStoreDTO
from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.banking.exceptions import CredentialsAlreadyExistError
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.value_objects import BankCredentials

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class StoreCredentialsCommand:
    """Persist encrypted bank credentials for the current user."""

    def __init__(
        self,
        credential_repository: BankCredentialRepository,
        uow: UnitOfWork,
    ):
        self._repo = credential_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> StoreCredentialsCommand:
        return cls(
            credential_repository=factory.credential_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self, credential_to_store: CredentialToStoreDTO) -> str:
        async with self._uow:
            existing = await self._repo.find_by_blz(credential_to_store.blz)
            if existing:
                raise CredentialsAlreadyExistError(blz=credential_to_store.blz)

            credentials = BankCredentials(
                blz=credential_to_store.blz,
                username=credential_to_store.username,
                pin=credential_to_store.pin,
            )

            return await self._repo.save(
                credentials=credentials,
                label=credentials.blz,
                tan_method=credential_to_store.tan_method,
                tan_medium=credential_to_store.tan_medium,
            )
