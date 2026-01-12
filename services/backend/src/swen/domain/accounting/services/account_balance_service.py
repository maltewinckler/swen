"""Account balance calculation service."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from swen.domain.accounting.value_objects.money import Money

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates.transaction import Transaction
    from swen.domain.accounting.entities.account import Account
    from swen.domain.accounting.repositories import AccountRepository

logger = logging.getLogger(__name__)


class AccountBalanceService:
    """Service for calculating account balances."""

    @staticmethod
    def calculate_balance(
        account: Account,
        transactions: List[Transaction],
        as_of_date: Optional[str] = None,
        include_drafts: bool = False,
    ) -> Money:
        balance = Money(0, account.default_currency)

        cutoff_date = AccountBalanceService._coerce_to_date(as_of_date)

        for transaction in transactions:
            transaction_date = AccountBalanceService._coerce_to_date(
                getattr(transaction, "date", None),
            )

            if cutoff_date and transaction_date and transaction_date > cutoff_date:
                continue

            if not include_drafts and not transaction.is_posted:
                continue

            entries_matched = 0
            for entry in transaction.entries:
                if entry.account == account:
                    entries_matched += 1
                    if account.account_type.is_debit_normal():
                        if entry.is_debit():
                            balance = balance + entry.amount
                        else:
                            balance = balance - entry.amount
                    elif entry.is_credit():
                        balance = balance + entry.amount
                    else:
                        balance = balance - entry.amount

            if entries_matched == 0 and len(transaction.entries) > 0:
                entry_account_ids = [str(e.account.id) for e in transaction.entries]
                logger.warning(
                    "Transaction %s has %d entries but none match account %s. "
                    "Entry account IDs: %s",
                    transaction.id,
                    len(transaction.entries),
                    account.id,
                    entry_account_ids,
                )

        return balance

    @staticmethod
    async def calculate_balance_with_children(
        account: Account,
        account_repo: AccountRepository,
        all_transactions: List[Transaction],
        as_of_date: Optional[str] = None,
        include_drafts: bool = False,
    ) -> Money:
        balance = AccountBalanceService.calculate_balance(
            account,
            all_transactions,
            as_of_date,
            include_drafts,
        )

        descendants = await account_repo.find_descendants(account.id)
        for child in descendants:
            child_balance = AccountBalanceService.calculate_balance(
                child,
                all_transactions,
                as_of_date,
                include_drafts,
            )
            balance = balance + child_balance

        return balance

    @staticmethod
    def get_trial_balance(
        accounts: List[Account],
        all_transactions: List[Transaction],
        as_of_date: Optional[str] = None,
    ) -> dict[UUID, Money]:
        """
        Generate a trial balance for all accounts.

        This allows verify_trial_balance() to simply sum all balances and
        check for zero (total debits = total credits).
        """
        trial_balance = {}

        for account in accounts:
            account_transactions = [
                t
                for t in all_transactions
                if any(entry.account == account for entry in t.entries)
            ]

            balance = AccountBalanceService.calculate_balance(
                account=account,
                transactions=account_transactions,
                as_of_date=as_of_date,
            )

            # Convert to signed debit convention for trial balance verification
            if not account.account_type.is_debit_normal():
                balance = Money(-balance.amount, balance.currency)

            trial_balance[account.id] = balance

        return trial_balance

    @staticmethod
    def verify_trial_balance(trial_balance: dict[UUID, Money]) -> bool:
        """
        Verify that the trial balance is balanced (total debits = total credits).

        Expects balances in signed debit convention (as returned by get_trial_balance):
        - Debit-normal accounts: positive values
        - Credit-normal accounts: negative values
        """
        if not trial_balance:
            return True

        # Get the first currency to ensure all balances are in same currency
        first_balance = next(iter(trial_balance.values()))
        total = Money(0, first_balance.currency)

        for balance in trial_balance.values():
            if balance.currency != total.currency:
                msg = "All balances must be in the same currency"
                raise ValueError(msg)
            total = total + balance

        return total.amount == 0

    @staticmethod
    def _coerce_to_date(raw_value: Optional[object]) -> Optional[date]:
        if raw_value is None:
            return None

        if isinstance(raw_value, datetime):
            return raw_value.date()

        if isinstance(raw_value, date):
            return raw_value

        if isinstance(raw_value, str):
            try:
                parsed = datetime.fromisoformat(raw_value)
            except ValueError as exc:
                msg = f"Invalid date value '{raw_value}'"
                raise ValueError(msg) from exc
            return parsed.date()

        msg = f"Unsupported date type: {type(raw_value).__name__}"
        raise TypeError(msg)
