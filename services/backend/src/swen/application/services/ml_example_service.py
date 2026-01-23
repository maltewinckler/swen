"""Service for extracting and submitting ML training examples from transactions."""

from __future__ import annotations

import logging
from decimal import Decimal

from swen.application.ports.ml_service import MLServicePort, TransactionExample
from swen.domain.accounting import WellKnownAccounts
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import AccountType

logger = logging.getLogger(__name__)


class MLExampleService:
    """Extracts transaction examples for ML training."""

    def __init__(self, ml_port: MLServicePort | None):
        self._ml_port = ml_port

    def submit_example(self, transaction: Transaction) -> None:
        """Submit a posted transaction as an ML training example.

        Skips submission if:
        - ML service is not available
        - Transaction has no expense/income counter-account
        - Counter-account is a fallback account (Sonstiges, Sonstige Einnahmen)
        """
        if self._ml_port is None or not self._ml_port.enabled:
            return

        counter_account = self._find_counter_account(transaction)
        if counter_account is None:
            return

        # Skip fallback accounts - don't train ML to use them
        if counter_account.account_number in WellKnownAccounts.FALLBACK_ACCOUNTS:
            logger.debug(
                "Skipping ML example for fallback account: %s",
                counter_account.account_number,
            )
            return

        amount = self._extract_amount(transaction)

        example = TransactionExample(
            user_id=transaction.user_id,
            account_id=counter_account.id,
            account_number=counter_account.account_number,
            transaction_id=transaction.id,
            purpose=transaction.description or "",
            amount=amount,
            counterparty_name=transaction.counterparty,
        )

        self._ml_port.submit_example(example)
        logger.debug(
            "Submitted ML example: txn=%s -> account=%s",
            transaction.id,
            counter_account.name,
        )

    def _find_counter_account(self, transaction: Transaction):
        for entry in transaction.entries:
            if entry.account.account_type in (AccountType.EXPENSE, AccountType.INCOME):
                return entry.account
        return None

    def _extract_amount(self, transaction: Transaction) -> Decimal:
        for entry in transaction.entries:
            if entry.is_debit():
                return entry.debit.amount
        return Decimal(0)
