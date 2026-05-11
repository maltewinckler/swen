"""Command to rename an imported bank account and its mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.dtos.accounting import BankAccountDTO
from swen.domain.integration.services import BankAccountImportService

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class RenameBankAccountCommand:
    """Rename an imported bank account and update the IBAN mapping.

    Encapsulates account-rename logic as an application-layer command so that
    the presentation layer never needs to instantiate domain services directly.
    """

    def __init__(self, import_service: BankAccountImportService) -> None:
        self._import_service = import_service

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> RenameBankAccountCommand:
        return cls(
            import_service=BankAccountImportService(
                account_repository=factory.account_repository(),
                mapping_repository=factory.account_mapping_repository(),
                current_user=factory.current_user,
                bank_account_repository=factory.bank_account_repository(),
            ),
        )

    async def execute(self, iban: str, new_name: str) -> BankAccountDTO:
        account, mapping = await self._import_service.rename_bank_account(
            iban=iban,
            new_name=new_name,
        )
        return BankAccountDTO.from_entities(account, mapping)
