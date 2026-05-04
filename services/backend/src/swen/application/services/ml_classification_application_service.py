"""Application service for applying ML classification results.

This service owns the business logic for:
1. Resolving an ML classification result to a validated account
2. Applying a classification to an existing draft Transaction
3. Determining if a transaction has a fallback counter-account

It uses ClassificationRules (domain service) for direction validation
and delegates ML communication to MLBatchClassificationService.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.domain.accounting.services.classification_rules import ClassificationRules
from swen.domain.accounting.well_known_accounts import WellKnownAccounts

if TYPE_CHECKING:
    from swen.application.services.ml_batch_classification_service import (
        BatchClassificationResult,
    )
    from swen.domain.accounting.aggregates import Transaction
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import AccountRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationApplicationResult:
    """Result of applying an ML classification to a transaction."""

    account: Account
    old_account: Account | None
    changed: bool
    confidence: float
    tier: str
    merchant: str | None
    is_recurring: bool
    recurring_pattern: str | None


class MLClassificationApplicationService:
    """Applies ML classification results to transactions.

    This service is the single source of truth for the business logic
    that determines whether an ML-suggested counter-account is valid
    and how to apply it to a transaction.
    """

    @staticmethod
    def is_valid_classification(
        is_money_outflow: bool,
        account: Account,
    ) -> bool:
        """Check if an ML result is valid for the given transaction direction.

        Parameters
        ----------
        is_money_outflow
            True if money is leaving the bank account
        account
            The account suggested by the ML model

        Returns
        -------
        bool
            True if the classification is valid and can be applied
        """
        return ClassificationRules.is_valid_counter_direction(
            is_money_outflow=is_money_outflow,
            account_type=account.account_type,
        )

    @staticmethod
    async def resolve_classification(
        ml_result: BatchClassificationResult,
        is_money_outflow: bool,
        account_repo: AccountRepository,
    ) -> Account | None:
        """Resolve an ML classification to a validated account.

        Looks up the account and validates direction compatibility.
        Returns None if the account doesn't exist or violates direction rules.

        Parameters
        ----------
        ml_result
            The ML classification result (must have counter_account_id set)
        is_money_outflow
            True if money is leaving the bank account
        account_repo
            Repository to look up the account

        Returns
        -------
        The validated account, or None if invalid/not found
        """
        if not ml_result.counter_account_id:
            return None

        account = await account_repo.find_by_id(ml_result.counter_account_id)
        if account is None:
            logger.warning(
                "ML result has account_id=%s but account not found in repository",
                ml_result.counter_account_id,
            )
            return None

        if not MLClassificationApplicationService.is_valid_classification(
            is_money_outflow=is_money_outflow,
            account=account,
        ):
            logger.warning(
                "ML direction mismatch: is_money_outflow=%s but ML returned "
                "%s account %s (%s). Rejecting classification.",
                is_money_outflow,
                account.account_type.value,
                account.account_number,
                account.name,
            )
            return None

        return account

    @staticmethod
    async def apply_to_transaction(
        txn: Transaction,
        ml_result: BatchClassificationResult,
        account_repo: AccountRepository,
    ) -> ClassificationApplicationResult | None:
        """Apply an ML classification to a draft transaction.

        Validates the classification, replaces unprotected entries, and
        updates ML metadata on the transaction. Does NOT persist — the
        caller must save.

        Parameters
        ----------
        txn
            Draft transaction to reclassify (must not be posted)
        ml_result
            The ML classification result
        account_repo
            Repository to look up accounts

        Returns
        -------
        ClassificationApplicationResult if classification was applied,
        None if the classification was invalid or unchanged.
        """
        if not ml_result.counter_account_id:
            return None

        new_account = await account_repo.find_by_id(ml_result.counter_account_id)
        if new_account is None:
            logger.warning(
                "ML returned account_id=%s but not found",
                ml_result.counter_account_id,
            )
            return None

        # Determine direction from protected (asset) entry
        is_money_outflow = _is_money_outflow(txn)

        # Direction guard
        if not MLClassificationApplicationService.is_valid_classification(
            is_money_outflow=is_money_outflow,
            account=new_account,
        ):
            logger.debug(
                "Direction mismatch for %s: ML suggested %s (%s)",
                txn.id,
                new_account.account_number,
                new_account.account_type.value,
            )
            return None

        # Check if this is actually a change
        current_counter = get_counter_account(txn)
        if current_counter and current_counter.id == new_account.id:
            return None  # Same account — no change

        old_account = current_counter

        # Build the replacement entry
        amount = txn.total_amount()
        is_debit = _counter_entry_is_debit(txn)
        txn.replace_unprotected_entries([(new_account, amount, is_debit)])

        # Update ML classification metadata
        txn.set_ml_classification(
            merchant=ml_result.merchant,
            is_recurring=ml_result.is_recurring,
            recurring_pattern=ml_result.recurring_pattern,
        )

        return ClassificationApplicationResult(
            account=new_account,
            old_account=old_account,
            changed=True,
            confidence=ml_result.confidence,
            tier=ml_result.tier,
            merchant=ml_result.merchant,
            is_recurring=ml_result.is_recurring,
            recurring_pattern=ml_result.recurring_pattern,
        )


# ═══════════════════════════════════════════════════════════════
#   Transaction utility functions (shared between import & reclassify)
# ═══════════════════════════════════════════════════════════════


def get_counter_account(txn: Transaction) -> Account | None:
    """Get the current counter-account (non-protected entry) of a transaction."""
    for entry in txn.entries:
        if not txn.is_entry_protected(entry):
            return entry.account
    return None


def has_fallback_counter_account(txn: Transaction) -> bool:
    """Check if the transaction's counter-account is a fallback account."""
    for entry in txn.entries:
        if (
            not txn.is_entry_protected(entry)
            and entry.account.account_number in WellKnownAccounts.FALLBACK_ACCOUNTS
        ):
            return True
    return False


def _is_money_outflow(txn: Transaction) -> bool:
    """Determine if a bank-import transaction represents money leaving.

    For bank imports, the protected entry is the asset entry.
    - Asset entry is CREDIT → money OUT (outflow)
    - Asset entry is DEBIT → money IN (inflow)
    """
    for entry in txn.entries:
        if txn.is_entry_protected(entry):
            return not entry.is_debit()  # Credit on asset = outflow
    # Fallback: treat as outflow (safer default for expenses)
    return True


def _counter_entry_is_debit(txn: Transaction) -> bool:
    """Determine if the counter-entry should be a debit or credit.

    The counter-entry is the opposite of the protected (asset) entry.
    """
    for entry in txn.entries:
        if txn.is_entry_protected(entry):
            # Counter is the opposite of the asset entry
            return not entry.is_debit()
    # Fallback: if no protected entry, use first entry direction
    return True
