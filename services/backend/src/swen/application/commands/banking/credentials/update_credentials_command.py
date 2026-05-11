"""Update stored bank credentials (partial update)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.banking import UpdateCredentialsDTO
from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.banking.exceptions import CredentialsNotFoundError
from swen.domain.banking.repositories import BankCredentialRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class UpdateCredentialsCommand:
    """Partially update already-stored bank credentials."""

    def __init__(
        self,
        credential_repository: BankCredentialRepository,
        uow: UnitOfWork,
    ):
        self._repo = credential_repository
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> UpdateCredentialsCommand:
        return cls(
            credential_repository=factory.credential_repository(),
            uow=factory.unit_of_work(),
        )

    async def execute(self, dto: UpdateCredentialsDTO) -> None:
        async with self._uow:
            existing = await self._repo.find_by_blz(dto.blz)
            if existing is None:
                raise CredentialsNotFoundError(blz=dto.blz)

            await self._repo.update(
                blz=dto.blz,
                username=dto.username,
                pin=dto.pin,
                tan_method=dto.tan_method,
                tan_medium=dto.tan_medium,
            )
