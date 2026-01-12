"""Query for bank connection details with reconciliation."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from swen.application.dtos.integration import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.services import AccountBalanceService
from swen.domain.banking.repositories import BankAccountRepository
from swen.domain.integration.repositories import AccountMappingRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class BankConnectionDetailsQuery:
    """Query to get details for a specific bank connection.

    For each bank account under the connection:
    1. Gets the bank-reported balance
    2. Calculates the bookkeeping balance
    3. Reports reconciliation status
    """

    # Tolerance for floating point comparison (in currency units)
    RECONCILIATION_TOLERANCE = Decimal("0.01")

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        mapping_repository: AccountMappingRepository,
        bank_account_repository: BankAccountRepository,
    ):
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._mapping_repo = mapping_repository
        self._bank_account_repo = bank_account_repository
        self._balance_service = AccountBalanceService()

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> BankConnectionDetailsQuery:
        return cls(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            mapping_repository=factory.account_mapping_repository(),
            bank_account_repository=factory.bank_account_repository(),
        )

    async def execute(self, blz: str) -> BankConnectionDetailsDTO | None:
        bank_accounts = await self._bank_account_repo.find_by_blz(blz)

        if not bank_accounts:
            return None

        account_details: list[BankAccountDetailDTO] = []
        reconciled_count = 0
        bank_name = None

        for bank_account in bank_accounts:
            if bank_name is None:
                bank_name = bank_account.bank_name

            mapping = await self._mapping_repo.find_by_iban(bank_account.iban)

            if mapping is None:
                continue

            accounting_account = await self._account_repo.find_by_id(
                mapping.accounting_account_id,
            )

            if accounting_account is None:
                continue

            transactions = await self._transaction_repo.find_by_account(
                mapping.accounting_account_id,
            )
            bookkeeping_balance = self._balance_service.calculate_balance(
                accounting_account,
                transactions,
                include_drafts=True,
            )

            bank_balance = bank_account.balance or Decimal("0")
            discrepancy = bank_balance - bookkeeping_balance.amount
            is_reconciled = abs(discrepancy) <= self.RECONCILIATION_TOLERANCE
            if is_reconciled:
                reconciled_count += 1

            account_details.append(
                BankAccountDetailDTO(
                    iban=bank_account.iban,
                    account_name=accounting_account.name,
                    account_type=bank_account.account_type or "Unknown",
                    currency=accounting_account.default_currency.code,
                    bank_balance=bank_balance,
                    bank_balance_date=bank_account.balance_date,
                    bookkeeping_balance=bookkeeping_balance.amount,
                    discrepancy=discrepancy,
                    is_reconciled=is_reconciled,
                ),
            )

        return BankConnectionDetailsDTO(
            blz=blz,
            bank_name=bank_name,
            accounts=tuple(account_details),
            total_accounts=len(account_details),
            reconciled_count=reconciled_count,
            discrepancy_count=len(account_details) - reconciled_count,
        )
