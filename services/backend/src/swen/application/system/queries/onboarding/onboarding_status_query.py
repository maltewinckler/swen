"""Onboarding status query checks user's setup progress.

This query derives the onboarding status from existing data:
- Are expense accounts initialized?
- Is at least one bank connected?
- Are there any transactions?
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.domain.accounting.entities import AccountType
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.banking.repositories import BankCredentialRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class OnboardingCompletedSteps:
    """Individual onboarding steps completion status."""

    accounts_initialized: bool
    first_bank_connected: bool
    has_transactions: bool


@dataclass
class OnboardingStatus:
    """Result of onboarding status query."""

    needs_onboarding: bool
    completed_steps: OnboardingCompletedSteps


class OnboardingStatusQuery:
    """Query to check user's onboarding status.

    This query determines whether a user needs to go through
    the onboarding flow by checking the state of their data:
    - Expense accounts exist (accounts initialized)
    - Bank credentials exist (bank connected)
    - Transactions exist (sync completed)
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        credential_repository: BankCredentialRepository,
    ):
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._credential_repo = credential_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> OnboardingStatusQuery:
        return cls(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            credential_repository=factory.credential_repository(),
        )

    async def execute(self) -> OnboardingStatus:
        expense_accounts = await self._account_repo.find_by_type(
            AccountType.EXPENSE.value,
        )
        accounts_initialized = len(expense_accounts) > 0

        credentials = await self._credential_repo.find_all()
        first_bank_connected = len(credentials) > 0

        transactions = await self._transaction_repo.find_all()
        has_transactions = len(transactions) > 0
        return OnboardingStatus(
            needs_onboarding=not accounts_initialized,
            completed_steps=OnboardingCompletedSteps(
                accounts_initialized=accounts_initialized,
                first_bank_connected=first_bank_connected,
                has_transactions=has_transactions,
            ),
        )
