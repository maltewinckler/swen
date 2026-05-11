"""Connect to a bank, fetch accounts, and import them."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from swen.application.dtos.banking import (
    BankAccountToImportDTO,
    ImportedBankAccountDTO,
    SetupBankRequestDTO,
    SetupBankResponseDTO,
)
from swen.domain.banking.repositories import (
    BankCredentialRepository,
)
from swen.domain.banking.services.bank_fetch_service import BankFetchService
from swen.domain.banking.value_objects import (
    BankAccount,
)
from swen.domain.integration.services import BankAccountImportService
from swen.infrastructure.banking.bank_connection_dispatcher import (
    BankConnectionDispatcher,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


logger = logging.getLogger(__name__)


class SetupBankCommand:
    """Coordinate bank connection and account import."""

    def __init__(
        self,
        bank_fetch_service: BankFetchService,
        import_service: BankAccountImportService,
        credential_repo: BankCredentialRepository,
    ):
        self._bank_fetch_service = bank_fetch_service
        self._import_service = import_service
        self._credential_repo = credential_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SetupBankCommand:
        return cls(
            bank_fetch_service=BankFetchService(
                bank_adapter=BankConnectionDispatcher.from_factory(factory)
            ),
            import_service=BankAccountImportService(
                account_repository=factory.account_repository(),
                mapping_repository=factory.account_mapping_repository(),
                current_user=factory.current_user,
                bank_account_repository=factory.bank_account_repository(),
            ),
            credential_repo=factory.credential_repository(),
        )

    async def execute(
        self,
        setup_bank_request: SetupBankRequestDTO,
    ) -> SetupBankResponseDTO:
        blz = setup_bank_request.blz

        imported_accounts = []
        for account in setup_bank_request.accounts:
            imported_bank_account = await self._import_single_account(account)
            imported_accounts.append(imported_bank_account)

        n = len(imported_accounts)
        logger.info("Bank setup successful for BLZ %s: %d accounts imported", blz, n)
        return SetupBankResponseDTO(
            blz=blz,
            imported_accounts=imported_accounts,
            success=True,
            message=f"Successfully imported {n} accounts for BLZ {blz}",
            warning=None,
        )

    async def _import_single_account(
        self,
        account_to_import: BankAccountToImportDTO,
    ) -> ImportedBankAccountDTO:
        raw_balance = account_to_import.balance
        raw_balance_date = account_to_import.balance_date
        balance = Decimal(raw_balance) if raw_balance else None
        balance_date = (
            datetime.fromisoformat(raw_balance_date) if raw_balance_date else None
        )
        bank_account = BankAccount(
            iban=account_to_import.iban,
            account_number=account_to_import.account_number,
            account_holder=account_to_import.account_holder,
            account_type=account_to_import.account_type,
            blz=account_to_import.blz,
            bic=account_to_import.bic,
            bank_name=account_to_import.bank_name,
            currency=account_to_import.currency,
            balance=balance,
            balance_date=balance_date,
        )

        accounting_account, _ = await self._import_service.import_bank_account(
            bank_account=bank_account,
            custom_name=account_to_import.custom_name,
        )

        return ImportedBankAccountDTO(
            **account_to_import.model_dump(),
            accounting_account_id=accounting_account.id,
        )
