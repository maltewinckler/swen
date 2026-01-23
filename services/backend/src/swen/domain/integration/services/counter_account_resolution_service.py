"""Counter-account resolution service for automatic transaction classification.

Resolution Strategy:
1. Rule-based matching (highest priority)
2. Return None (caller falls back to default "Sonstiges" account)

Note: AI-based resolution is handled upstream by MLBatchClassificationService.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen.domain.accounting.entities import Account
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.repositories import CounterAccountRuleRepository
from swen.domain.integration.value_objects import ResolutionResult

if TYPE_CHECKING:
    from swen.domain.accounting.repositories import AccountRepository

logger = logging.getLogger(__name__)


class CounterAccountResolutionService:
    """Service for automatically resolving the Counter-Account for bank transactions.

    This service handles rule-based resolution only. AI/ML-based classification
    is handled separately by MLBatchClassificationService before this service
    is invoked.
    """

    def __init__(
        self,
        rule_repository: CounterAccountRuleRepository,
        user_id: UUID | None = None,
    ):
        self._rule_repository = rule_repository
        self._user_id = user_id

    async def resolve_counter_account(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> Account | None:
        result = await self._resolve_with_details(
            bank_transaction=bank_transaction,
            account_repository=account_repository,
        )
        return result.account

    async def resolve_counter_account_with_details(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> ResolutionResult:
        return await self._resolve_with_details(
            bank_transaction=bank_transaction,
            account_repository=account_repository,
        )

    async def _resolve_with_details(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> ResolutionResult:
        # Try rule-based matching
        account = await self._resolve_with_rules(
            bank_transaction=bank_transaction,
            account_repository=account_repository,
        )
        if account:
            return ResolutionResult(account=account, source="rule")

        # No match found
        return ResolutionResult(account=None, source="none")

    async def get_fallback_account(
        self,
        is_expense: bool,
        account_repository: AccountRepository,
    ) -> Account:
        if is_expense:
            # Money out = Expense
            account_number = WellKnownAccounts.FALLBACK_EXPENSE
            default_account = await account_repository.find_by_account_number(
                account_number
            )
            if not default_account:
                msg = f"Default expense account ({account_number}) not found"
                raise ValueError(msg)
        else:
            # Money in = Income
            account_number = WellKnownAccounts.FALLBACK_INCOME
            default_account = await account_repository.find_by_account_number(
                account_number
            )
            if not default_account:
                msg = f"Default income account ({account_number}) not found"
                raise ValueError(msg)

        return default_account

    async def _resolve_with_rules(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> Account | None:
        # Get all active rules (already sorted by priority)
        rules = await self._rule_repository.find_all_active()

        # Find first matching rule
        for rule in rules:
            if rule.matches(bank_transaction):
                # Record that this rule was used
                rule.record_match()
                await self._rule_repository.save(rule)

                # Fetch the counter-account
                return await account_repository.find_by_id(
                    rule.counter_account_id,
                )

        return None
