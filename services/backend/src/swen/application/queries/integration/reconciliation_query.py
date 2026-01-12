"""Reconciliation query. Compare bank balances with bookkeeping balances."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from swen.application.dtos.integration import (
    AccountReconciliationDTO,
    ReconciliationResultDTO,
)
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.accounting.services import AccountBalanceService
from swen.domain.banking.repositories import BankAccountRepository
from swen.domain.integration.repositories import AccountMappingRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class ReconciliationQuery:
    """Query to compare bank balances with bookkeeping balances.

    For each linked bank account, this query:
    1. Gets the bank-reported balance (from last sync)
    2. Calculates the bookkeeping balance (from accounting transactions)
    3. Reports any discrepancies
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
    def from_factory(cls, factory: RepositoryFactory) -> ReconciliationQuery:
        return cls(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            mapping_repository=factory.account_mapping_repository(),
            bank_account_repository=factory.bank_account_repository(),
        )

    async def execute(self) -> ReconciliationResultDTO:
        mappings = await self._mapping_repo.find_all()

        results: list[AccountReconciliationDTO] = []
        reconciled_count = 0

        for mapping in mappings:
            if not mapping.is_active:
                continue

            bank_account = await self._bank_account_repo.find_by_iban(mapping.iban)
            if bank_account is None:
                continue

            accounting_account = await self._account_repo.find_by_id(
                mapping.accounting_account_id,
            )
            if accounting_account is None:
                continue

            transactions = await self._transaction_repo.find_by_account(
                mapping.accounting_account_id,
            )

            logger.debug(
                "Reconciliation for %s: found %d transactions for account %s",
                mapping.iban,
                len(transactions),
                mapping.accounting_account_id,
            )

            bookkeeping_balance = self._balance_service.calculate_balance(
                accounting_account,
                transactions,
                include_drafts=True,  # Include drafts for accurate comparison
            )

            bank_balance = bank_account.balance or Decimal("0")
            discrepancy = bank_balance - bookkeeping_balance.amount
            if abs(discrepancy) > self.RECONCILIATION_TOLERANCE:
                logger.warning(
                    "Reconciliation discrepancy %s: bank=%s, bookkeeping=%s, diff=%s",
                    mapping.iban,
                    bank_balance,
                    bookkeeping_balance.amount,
                    discrepancy,
                )

            is_reconciled = abs(discrepancy) <= self.RECONCILIATION_TOLERANCE

            if is_reconciled:
                reconciled_count += 1

            results.append(
                AccountReconciliationDTO(
                    iban=mapping.iban,
                    account_name=accounting_account.name,
                    accounting_account_id=str(mapping.accounting_account_id),
                    currency=accounting_account.default_currency.code,
                    bank_balance=bank_balance,
                    bank_balance_date=bank_account.balance_date,
                    last_sync_at=None,  # TODO: Add last_sync_at to BankAccount?
                    bookkeeping_balance=bookkeeping_balance.amount,
                    discrepancy=discrepancy,
                    is_reconciled=is_reconciled,
                ),
            )

        return ReconciliationResultDTO(
            accounts=tuple(results),
            total_accounts=len(results),
            reconciled_count=reconciled_count,
            discrepancy_count=len(results) - reconciled_count,
        )
