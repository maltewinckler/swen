"""Counter-account resolution service for automatic transaction classification.

Resolution Strategy:
1. Rule-based matching (highest priority -> not existing yet!!)
2. AI resolution (if configured and no rules match)
3. Return None (caller falls back to default "Sonstiges" account)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from swen.domain.accounting.entities import Account
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.repositories import CounterAccountRuleRepository
from swen.domain.integration.services.ai_counter_account_provider import (
    AICounterAccountProvider,
)
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    CounterAccountOption,
    ResolutionResult,
)

if TYPE_CHECKING:
    from swen.domain.accounting.repositories import AccountRepository

logger = logging.getLogger(__name__)


class CounterAccountResolutionService:
    """Service for automatically resolving the Counter-Account for bank transactions."""

    def __init__(
        self,
        rule_repository: CounterAccountRuleRepository,
        ai_provider: Optional[AICounterAccountProvider] = None,
    ):
        self._rule_repository = rule_repository
        self._ai_provider = ai_provider

    @property
    def has_ai_provider(self) -> bool:
        return self._ai_provider is not None

    async def resolve_counter_account(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> Optional[Account]:
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
        # Step 1: Try rule-based matching first
        account = await self._resolve_with_rules(
            bank_transaction=bank_transaction,
            account_repository=account_repository,
        )
        if account:
            return ResolutionResult(account=account, source="rule")

        # Step 2: Try AI resolution if available
        if self._ai_provider:
            ai_result, is_confident = await self._resolve_with_ai(
                bank_transaction=bank_transaction,
                account_repository=account_repository,
            )
            if ai_result:
                if is_confident:
                    # Fetch the account for confident results
                    account = await account_repository.find_by_id(
                        ai_result.counter_account_id,
                    )
                    if account:
                        logger.info(
                            "AI resolved counter-account: %s (confidence: %.2f)",
                            account.name,
                            ai_result.confidence,
                        )
                        return ResolutionResult(
                            account=account,
                            ai_result=ai_result,
                            source="ai",
                        )
                else:
                    # Low confidence - preserve AI result but don't use account
                    logger.info(
                        "AI low confidence (%.2f) - will use fallback, "
                        "but preserving AI metadata",
                        ai_result.confidence,
                    )
                    return ResolutionResult(
                        account=None,
                        ai_result=ai_result,
                        source="ai_low_confidence",
                    )

        # Step 3: No match found (no rules, no AI result)
        return ResolutionResult(account=None, source="none")

    async def get_fallback_account(
        self,
        is_expense: bool,
        account_repository: AccountRepository,
    ) -> Account:
        if is_expense:
            # Money out = Expense
            # Look for "Sonstiges" expense account (code 4900)
            default_account = await account_repository.find_by_account_number("4900")
            if not default_account:
                msg = "Default expense account (Sonstiges - 4900) not found"
                raise ValueError(msg)
        else:
            # Money in = Income
            # Look for "Sonstige Einnahmen" income account (code 3100)
            default_account = await account_repository.find_by_account_number("3100")
            if not default_account:
                msg = "Default income account (Sonstige Einnahmen - 3100) not found"
                raise ValueError(msg)

        return default_account

    async def _resolve_with_rules(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> Optional[Account]:
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

    async def _resolve_with_ai(
        self,
        bank_transaction: BankTransaction,
        account_repository: AccountRepository,
    ) -> tuple[Optional[AICounterAccountResult], bool]:
        if not self._ai_provider:
            return None, False

        try:
            # Get available expense and income accounts
            available_accounts = await self._get_available_counter_accounts(
                account_repository,
            )

            if not available_accounts:
                logger.warning("No expense/income accounts available for AI resolution")
                return None, False

            # Call AI provider
            result = await self._ai_provider.resolve(
                transaction=bank_transaction,
                available_accounts=available_accounts,
            )

            if not result:
                logger.debug("AI provider returned no result")
                return None, False

            # Validate that the suggested account exists
            valid_ids = {acc.account_id for acc in available_accounts}
            if result.counter_account_id not in valid_ids:
                logger.warning(
                    "AI suggested invalid account ID: %s",
                    result.counter_account_id,
                )
                return None, False

            # Check confidence threshold
            threshold = self._ai_provider.min_confidence_threshold
            is_confident = result.is_confident(threshold)

            if not is_confident:
                logger.debug(
                    "AI confidence %.2f below threshold %.2f",
                    result.confidence,
                    threshold,
                )

            # Return result with confidence status (result is preserved either way)
            return result, is_confident

        except Exception as e:
            # AI failures should not break the import flow
            logger.warning(
                "AI resolution failed (falling back to default): %s",
                str(e),
            )
            return None, False

    async def _get_available_counter_accounts(
        self,
        account_repository: AccountRepository,
    ) -> list[CounterAccountOption]:
        # Fetch all accounts and filter to expense/income types
        all_accounts = await account_repository.find_all()

        options = []
        for account in all_accounts:
            account_type_str = account.account_type.value.lower()
            if account_type_str in ("expense", "income"):
                options.append(
                    CounterAccountOption(
                        account_id=account.id,
                        account_number=account.account_number,
                        name=account.name,
                        account_type=account_type_str,
                        description=account.description,
                    ),
                )

        return options
