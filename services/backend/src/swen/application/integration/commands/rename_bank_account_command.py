"""Command to rename an imported bank account and its mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.accounting.dtos import BankAccountDTO
from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.integration.services import BankAccountImportService

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class RenameBankAccountCommand:
    """Rename an imported bank account and update the IBAN mapping.

    Encapsulates account-rename logic as an application-layer command so that
    the presentation layer never needs to instantiate domain services directly.
    """

    def __init__(
        self,
        import_service: BankAccountImportService,
        uow: UnitOfWork,
    ) -> None:
        self._import_service = import_service
        self._uow = uow

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> RenameBankAccountCommand:
        return cls(
            import_service=BankAccountImportService(
                account_repository=factory.account_repository(),
                mapping_repository=factory.account_mapping_repository(),
                current_user=factory.current_user,
                bank_account_repository=factory.bank_account_repository(),
            ),
            uow=factory.unit_of_work(),
        )

    async def execute(self, iban: str, new_name: str) -> BankAccountDTO:
        async with self._uow:
            account, mapping = await self._import_service.rename_bank_account(
                iban=iban,
                new_name=new_name,
            )
            return BankAccountDTO.from_entities(account, mapping)
